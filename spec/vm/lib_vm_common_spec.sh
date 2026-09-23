# shellcheck shell=bash
#
# Functional unit tests for vm/lib-vm-common.sh
#
# These tests source the library and exercise its pure functions.
# Functions requiring libvirt (virsh, virt-install) are not tested here.

Describe "validate_ip()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "accepts a valid IPv4 address"
    When call validate_ip "192.168.1.1"
    The status should be success
  End

  It "accepts 0.0.0.0"
    When call validate_ip "0.0.0.0"
    The status should be success
  End

  It "accepts 255.255.255.255"
    When call validate_ip "255.255.255.255"
    The status should be success
  End

  It "rejects non-dotted-quad format"
    When call validate_ip "not-an-ip"
    The status should be failure
    The stderr should include "Invalid"
  End

  It "rejects too few octets"
    When call validate_ip "192.168.1"
    The status should be failure
    The stderr should include "Invalid"
  End

  It "rejects octet > 255"
    When call validate_ip "192.168.1.256"
    The status should be failure
    The stderr should include "out of range"
  End

  It "rejects empty string"
    When call validate_ip ""
    The status should be failure
    The stderr should include "Invalid"
  End

  It "uses custom label in error message"
    When call validate_ip "bad" "Gateway"
    The status should be failure
    The stderr should include "Gateway"
  End
End

Describe "log_info()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "outputs to stderr, not stdout"
    When call log_info "test message"
    The stderr should include "[INFO]"
    The output should equal ""
  End

  It "includes the message text"
    When call log_info "hello world"
    The stderr should include "hello world"
  End
End

Describe "log_warn()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "outputs to stderr"
    When call log_warn "warning message"
    The stderr should include "[WARN]"
    The output should equal ""
  End
End

Describe "log_error()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "outputs to stderr"
    When call log_error "error message"
    The stderr should include "[ERROR]"
    The output should equal ""
  End
End

Describe "die()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "exits with code 1 by default"
    When run die "fatal error"
    The status should equal 1
    The stderr should include "[ERROR]"
    The stderr should include "fatal error"
  End

  It "accepts a custom exit code"
    When run die "custom exit" 42
    The status should equal 42
    The stderr should include "[ERROR]"
    The stderr should include "custom exit"
  End
End

Describe "ERR diagnostics"
  It "reports the original nonzero status"
    # shellcheck disable=SC2016 # Variables expand in the nested bash -c process.
    When run bash -c '
      source "$1"
      source "$2"
      python3() { return 7; }
      hermes_luks_console_unlock lab-hermes-server qemu:///system 1 /tmp/hermes-luks-test.log
    ' _ "$PROJECT_ROOT/vm/lib-vm-common.sh" "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
    The status should equal 7
    The stderr should include "exited 7"
    The stderr should not include "exited 0"
  End
End

Describe "require_cmd()"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "succeeds for an existing command (bash)"
    When call require_cmd "bash"
    The status should be success
  End

  It "fails for a nonexistent command"
    When call require_cmd "__nonexistent_command_xyz__"
    The status should be failure
    The stderr should include "Required command not found"
  End
End

Describe "include guard"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  It "sets _LIB_VM_COMMON_LOADED after sourcing"
    The variable _LIB_VM_COMMON_LOADED should equal "1"
  End
End

Describe "NO_COLOR support"
  Include "$PROJECT_ROOT/vm/lib-vm-common.sh"

  # When NO_COLOR is set, color variables should be empty.
  # This test verifies the mechanism exists; it may need the library
  # re-sourced with NO_COLOR=1 which readonly prevents. We verify
  # the code path exists via the static standards_spec.sh checks.
  It "has NO_COLOR check in source"
    When call grep -c 'NO_COLOR' "$PROJECT_ROOT/vm/lib-vm-common.sh"
    The output should not equal "0"
  End
End
