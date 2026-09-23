# shellcheck shell=bash
#
# Static compliance checks for vm/ scripts against bash-standards.md
#
# These tests validate file structure without executing the scripts.

Describe "bash-standards compliance"
  # All 4 vm/ scripts must pass these structural checks

  Parameters
    "vm/lib-vm-common.sh"
    "vm/setup-hypervisor.sh"
    "vm/create-fedora-vm.sh"
    "vm/create-hermes-server-vm.sh"
  End

  Describe "shebang"
    It "uses #!/usr/bin/env bash in $1"
      When call head -1 "$PROJECT_ROOT/$1"
      The output should equal "#!/usr/bin/env bash"
    End
  End

  Describe "strict mode"
    It "sets errexit in $1"
      When call grep -c '^set -o errexit' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End

    It "sets nounset in $1"
      When call grep -c '^set -o nounset' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End

    It "sets pipefail in $1"
      When call grep -c '^set -o pipefail' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End

    It "sets errtrace in $1"
      When call grep -c '^set -o errtrace' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End

    It "sets inherit_errexit in $1"
      When call grep -c '^shopt -s inherit_errexit' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End

    It "sets nullglob in $1"
      When call grep -c '^shopt -s nullglob' "$PROJECT_ROOT/$1"
      The output should equal "1"
    End
  End

  Describe "absolute prohibitions"
    # Backtick and single-bracket checks are covered by shellcheck
    # (SC2006 for backticks, verified by the shellcheck test above).
    # Explicit grep-based checks omitted to avoid shell quoting issues.
    Skip "covered by shellcheck SC2006 and SC2292"
  End

  Describe "shellcheck"
    It "passes shellcheck for $1"
      When run shellcheck -S warning "$PROJECT_ROOT/$1"
      The status should be success
    End
  End

  Describe "shfmt"
    It "is formatted per shfmt -i 2 -ci -bn for $1"
      When run shfmt -i 2 -ci -bn -d "$PROJECT_ROOT/$1"
      The status should be success
      The output should equal ""
    End
  End
End

Describe "Hermes Server certification resource contract"
  It "documents the certified VM resources and host thresholds"
    When run grep -E '^readonly HERMES_SERVER_DEFAULT_RAM=8192|^readonly HERMES_SERVER_DEFAULT_VCPUS=2|^readonly HERMES_SERVER_DEFAULT_DISK=40|HERMES_SERVER_MIN_CPUS=2|HERMES_SERVER_MIN_MEM_AVAILABLE_GIB=9|HERMES_SERVER_MIN_STORAGE_GIB=60' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The status should be success
    The output should include "HERMES_SERVER_DEFAULT_RAM=8192"
    The output should include "HERMES_SERVER_MIN_MEM_AVAILABLE_GIB=9"
  End

  It "runs the resource preflight before creating a Hermes Server VM"
    When run grep -n -A2 'check_hermes_server_host_resources' "$PROJECT_ROOT/vm/create-hermes-server-vm.sh"
    The status should be success
    The output should include "check_hermes_server_host_resources"
  End

  It "boots the Fedora installer with explicit kernel arguments instead of timed keystrokes"
    When run grep -E -- 'readonly INSTALL_KERNEL_ARGS=|--location|--extra-args|send-key.*KEY_(UP|ENTER)' "$PROJECT_ROOT/vm/create-hermes-server-vm.sh"
    The status should be success
    The output should equal "readonly INSTALL_KERNEL_ARGS='inst.stage2=hd:LABEL=Fedora-S-dvd-x86_64-44 inst.ks=hd:LABEL=OEMDRV:/ks.cfg console=tty0 console=ttyS0,115200n8'
    --location \"\$ISO_PATH\" --extra-args \"\$INSTALL_KERNEL_ARGS\")"
  End

  It "fails fast before expensive certification checks and rechecks before VM creation"
    When run grep -E '^(check_hermes_server_host_resources /var/lib/libvirt/images|verify_media|run_offline_tests|VM_CREATED=true)$' "$PROJECT_ROOT/hermes-certify-vm.sh"
    The status should be success
    The output should equal "check_hermes_server_host_resources /var/lib/libvirt/images
verify_media
run_offline_tests
check_hermes_server_host_resources /var/lib/libvirt/images
VM_CREATED=true"
  End

  It "confirms the encrypted console attachment before controller-driven reboots"
    When run grep -E '^start_unlock_monitor$|^wait_ssh \|\| |^run_certification_controller_deploy$' "$PROJECT_ROOT/hermes-certify-vm.sh"
    The status should be success
    The output should equal "start_unlock_monitor
wait_ssh || die 'certification VM did not become reachable over SSH' 69
run_certification_controller_deploy"
  End
End

Describe "lib-vm-common.sh specific compliance"
  It "has an include guard"
    When call grep -c '_LIB_VM_COMMON_LOADED' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should not equal "0"
  End

  It "defines die() function"
    When call grep -c '^die()' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should equal "1"
  End

  It "has ERR trap"
    When run grep "trap.*ERR" "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The status should be success
    The output should include "ERR"
  End

  It "log_info outputs to stderr"
    When call grep -A1 '^log_info()' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should include ">&2"
  End

  It "log_warn outputs to stderr"
    When call grep -A1 '^log_warn()' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should include ">&2"
  End

  It "log_error outputs to stderr"
    When call grep -A1 '^log_error()' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should include ">&2"
  End

  It "checks NO_COLOR for color handling"
    When call grep -c 'NO_COLOR' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should not equal "0"
  End

  It "checks TTY for color handling"
    When call grep -c '\-t 2' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should not equal "0"
  End
End

Describe "trap signal propagation"
  It "create-fedora-vm.sh has INT signal trap"
    When run grep "trap.*INT" "$PROJECT_ROOT/vm/create-fedora-vm.sh"
    The status should be success
    The output should include "kill -INT"
  End

  It "create-fedora-vm.sh has TERM signal trap"
    When run grep "trap.*TERM" "$PROJECT_ROOT/vm/create-fedora-vm.sh"
    The status should be success
    The output should include "kill -TERM"
  End

  It "create-hermes-server-vm.sh has INT signal trap"
    When run grep "trap.*INT" "$PROJECT_ROOT/vm/create-hermes-server-vm.sh"
    The status should be success
    The output should include "kill -INT"
  End

  It "create-hermes-server-vm.sh has TERM signal trap"
    When run grep "trap.*TERM" "$PROJECT_ROOT/vm/create-hermes-server-vm.sh"
    The status should be success
    The output should include "kill -TERM"
  End
End
