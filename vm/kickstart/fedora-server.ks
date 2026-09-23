# Fedora Server 44 automated installation for the disposable Hermes certifier.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
cdrom
bootloader --append="rd.auto=1 console=tty0 console=ttyS0,115200n8"

zerombr
clearpart --all --initlabel
# Retain recovery images and space for bounded boot-artifact probes.
part /boot/efi --fstype=efi --ondisk=vda --size=2048
part /boot --fstype=ext4 --ondisk=vda --size=1024
part pv.01 --ondisk=vda --size=1 --grow --encrypted --passphrase=hermes-e2e-fixture
volgroup vg_root pv.01
logvol swap --recommended --name=swap --vgname=vg_root
logvol / --fstype=xfs --size=6144 --grow --name=root --vgname=vg_root

network --bootproto=static --ip=172.16.99.12 --netmask=255.255.255.0 --gateway=172.16.99.1 --nameserver=172.16.99.1 --device=link --activate --onboot=on --hostname=lab-hermes-server

user --name=lab --lock --groups=wheel
rootpw --lock
services --enabled=sshd,firewalld
firewall --enabled --service=ssh

%packages
@^server-product-environment
dnf5
firewalld
curl
openssl
python3
podman
mokutil
lvm2
openssh-server
sudo
%end

poweroff

%post --log=/root/ks-post.log
# HERMES_SSH_KEY_PLACEHOLDER
cat >/etc/sudoers.d/lab-hermes-fixture <<'EOF'
lab ALL=(root) NOPASSWD: /usr/bin/bash
EOF
chmod 0440 /etc/sudoers.d/lab-hermes-fixture

install -d -o root -g root -m 0755 /etc/systemd/resolved.conf.d
cat >/etc/systemd/resolved.conf.d/60-hermes-server-e2e.conf <<'EOF'
[Resolve]
LLMNR=no
MulticastDNS=no
EOF

for unit in \
  avahi-daemon.service avahi-daemon.socket \
  cups.service cups.socket cups.path passim.service \
  cockpit.service cockpit.socket cockpit-motd.service; do
  ln -sfn /dev/null "/etc/systemd/system/$unit"
done

install -d -o root -g root -m 0755 /etc/dracut.conf.d
cat >/etc/dracut.conf.d/99-hermes-server-e2e-luks.conf <<'EOF'
hostonly="yes"
hostonly_cmdline="yes"
add_dracutmodules+=" crypt lvm "
EOF
echo kickstart-provisioned >/root/.vm-provisioned
%end
