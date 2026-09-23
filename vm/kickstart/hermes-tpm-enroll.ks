
# Disposable TPM fixture only. Appended by --tpm-stage after the base kickstart.
# The existing fixture passphrase remains a recovery option; no console input is sent.
%pre --erroronfail --log=/tmp/hermes-tpm-preflight.log
set -eu
python3 - <<'PCRCHECK'
from pathlib import Path
for index in (7, 11):
    value = Path(f"/sys/class/tpm/tpm0/pcr-sha256/{index}").read_text().strip()
    if len(value) != 64 or int(value, 16) in (0, 2**256 - 1):
        raise SystemExit(f"Unmeasured SHA256 PCR{index}; TPM staging rejected")
PCRCHECK
%end

%post --nochroot --erroronfail --log=/mnt/sysroot/root/hermes-uki-installer-check.log
set -eu
test -s /run/systemd/tpm2-pcr-public-key.pem
test -s /run/systemd/tpm2-pcr-signature.json
install -d -m 0755 /mnt/sysroot/run/systemd
# The target's resolver is a runtime symlink; preserve DNS in the installer chroot.
install -d -m 0755 /mnt/sysroot/run/systemd/resolve
if ! [ /etc/resolv.conf -ef /mnt/sysroot/run/systemd/resolve/stub-resolv.conf ]; then
  install -m 0644 /etc/resolv.conf /mnt/sysroot/run/systemd/resolve/stub-resolv.conf
fi
install -m 0644 /run/systemd/tpm2-pcr-public-key.pem /mnt/sysroot/run/systemd/installer-pcr-public-key.pem
install -m 0644 /run/systemd/tpm2-pcr-signature.json /mnt/sysroot/run/systemd/installer-pcr-signature.json
# Apply the standard profile to the offline target before its initrds are built.
# This is the disposable installer environment, not a live-host migration helper.
install -d -m 0700 /run/hermes-profile-oem
mount -o ro /dev/disk/by-label/OEMDRV /run/hermes-profile-oem
trap 'umount /run/hermes-profile-oem' EXIT
python3 -I -B - <<'TPMPROFILE'
import sys
from pathlib import Path
sys.path.insert(0, '/run/hermes-profile-oem')
from tpm_profile import render
render(Path('/mnt/sysroot').resolve(strict=True))
TPMPROFILE
umount /run/hermes-profile-oem
trap - EXIT
%end

%post --erroronfail --log=/root/hermes-tpm-enrollment.log
set -eu
test -c /dev/tpmrm0
test -b /dev/vda3
cryptsetup isLuks --type luks2 /dev/vda3
mokutil --sb-state | grep -q 'SecureBoot enabled'
python3 - <<'PCRCHECK'
from pathlib import Path
for index in (7, 11):
    value = Path(f"/sys/class/tpm/tpm0/pcr-sha256/{index}").read_text().strip()
    if len(value) != 64 or int(value, 16) in (0, 2**256 - 1):
        raise SystemExit(f"Unmeasured SHA256 PCR{index}; TPM staging rejected")
PCRCHECK
# The Server DVD omits tpm2-tools, which dracut's tpm2-tss module requires.
# Use only the signed Fedora 44 release repository; no updates or disabled checks.
timeout --signal=TERM --kill-after=10s 300s dnf5 --releasever=44 \
  --disable-repo='*' --enable-repo=fedora --setopt=fedora.gpgcheck=1 \
  --assumeyes install tpm2-tools
install -d -m 0700 /run/hermes-oem
mount -o ro /dev/disk/by-label/OEMDRV /run/hermes-oem
trap 'rm -f /run/hermes-enrollment.key; umount /run/hermes-oem' EXIT
install -d -m 0755 /etc/systemd
install -m 0644 /run/hermes-oem/tpm2-pcr-public-key.pem /etc/systemd/tpm2-pcr-public-key.pem
cmp /run/systemd/installer-pcr-public-key.pem /etc/systemd/tpm2-pcr-public-key.pem
umask 077
printf '%s' 'hermes-e2e-fixture' >/run/hermes-enrollment.key
systemd-cryptenroll --unlock-key-file=/run/hermes-enrollment.key \
  --tpm2-device=/dev/tpmrm0 --tpm2-pcrs=7:sha256 --tpm2-public-key-pcrs=11 \
  --tpm2-public-key=/etc/systemd/tpm2-pcr-public-key.pem --tpm2-with-pin=no \
  --tpm2-signature=/run/systemd/installer-pcr-signature.json \
  --tpm2-pcrlock= /dev/vda3
install -d -m 0755 /etc/dracut.conf.d
cat >/etc/dracut.conf.d/98-hermes-tpm.conf <<'EOF'
add_dracutmodules+=" tpm2-tss "
EOF
dracut --regenerate-all --force
# Export only public boot inputs after dracut; never export the recovery key or root data.
export_dir=/boot/efi/hermes-boot-inputs
install -d -m 0755 "$export_dir"
kernel_version=$(rpm -q kernel-core --qf '%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort -V | tail -n 1)
test -n "$kernel_version"
install -m 0644 "/boot/vmlinuz-$kernel_version" "$export_dir/linux"
install -m 0644 "/boot/initramfs-$kernel_version.img" "$export_dir/initrd"
install -m 0644 /etc/os-release "$export_dir/osrel"
luks_uuid=$(cryptsetup luksUUID /dev/vda3)
printf 'root=/dev/mapper/vg_root-root ro rd.lvm.lv=vg_root/root rd.luks.uuid=luks-%s rd.luks.options=tpm2-device=auto\n' \
  "$luks_uuid" >"$export_dir/cmdline"
(cd "$export_dir" && sha256sum linux initrd osrel cmdline >SHA256SUMS)
# Public stage binding on the unencrypted ESP for the shutoff-disk handoff.
install -m 0644 /etc/systemd/tpm2-pcr-public-key.pem /boot/efi/hermes-pcr-public-key.pem
printf '%s\n' 'hermes-disposable-tpm-stage-v1' >/boot/efi/hermes-tpm-stage
printf '%s\n' 'tpm-enrolled-awaiting-signed-uki' >/root/.hermes-tpm-stage
%end
