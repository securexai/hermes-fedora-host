# shellcheck shell=bash
# The sourced library and mock are resolved/invoked dynamically by ShellSpec;
# the literal GRUB transcript must not expand its captured `$root` token.
# shellcheck disable=SC1091,SC2016,SC2329

write_virsh_console_fixture() {
  local work_dir=$1
  mkdir -p "$work_dir/bin"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'if [[ "${TEST_REQUIRE_TTY:-0}" == 1 && ! -t 0 ]]; then' \
    '  printf "interactive console requires tty\\n"' \
    '  exit 1' \
    'fi' \
    'if [[ "${TEST_EXIT_EARLY:-0}" == 1 ]]; then' \
    '  printf "%s\\n" "${TEST_EXIT_TEXT:-console process exited}"' \
    '  exit 1' \
    'fi' \
    'stty -echo 2>/dev/null || true' \
    'printf "Connected to domain fixture\\nEscape character is ^] (Ctrl + ])\\n"' \
    'if [[ -n "${TEST_PROMPT_TRIGGER:-}" ]]; then' \
    '  while [[ ! -e "$TEST_PROMPT_TRIGGER" ]]; do sleep 0.01; done' \
    'fi' \
    'if [[ "${TEST_SEQUENTIAL_PROMPTS:-0}" == 1 ]]; then' \
    '  prompt_index=0' \
    '  for marker in "$TEST_FIRST_SUBMISSION_MARKER" "$TEST_SECOND_SUBMISSION_MARKER"; do' \
    '    prompt_index=$((prompt_index + 1))' \
    '    if [[ "${TEST_QUIET_BOOT_BOUNDARY:-0}" == 1 ]]; then' \
    '      printf "[  OK  ] Reached target paths.target - Path Units.\n"' \
    '    fi' \
    '    if [[ "${TEST_IN_PLACE_STATUS_REPAINT:-0}" == 1 ]]; then' \
    '      printf "\r[ *** ] A start job is running for encrypted root\b"' \
    '    fi' \
    '    printf "%s\n" "Reached target reboot.target - System Reboot."' \
    '    if [[ "${TEST_ELLIPSIZED_CRYPTSETUP:-0}" == 1 ]]; then' \
    '      printf "%b\n" "Starting \\033[0;1;39msystemd-cryptsetup@luks\\\\x…\\033[0m6582-4843-4be6-8502-44d290746e0d..."' \
    '    else' \
    '      printf "%s\n" "Starting systemd-cryptsetup@luks\\x2dexample.service - Cryptography Setup for luks-example"' \
    '    fi' \
    '    printf "Please enter passphrase for disk luks-example:"' \
    '    submitted=""' \
    '    IFS= read -r -t 3 submitted || true' \
    '    [[ -n "$submitted" ]] && : >"$marker"' \
    '    if [[ "${TEST_POST_UNLOCK_PROGRESS:-0}" == 1 ]]; then' \
    '      printf "\n[  OK  ] Reached target paths.target - Path Units.\n"' \
    '    fi' \
    '    if [[ "$prompt_index" == 1 && "${TEST_DUPLICATE_FIRST_PROMPT:-0}" == 1 ]]; then' \
    '      if [[ "${TEST_PROGRESS_BEFORE_DUPLICATE:-0}" == 1 ]]; then' \
    '        printf "\n[  OK  ] Reached target Local Encrypted Volumes.\n"' \
    '      fi' \
    '      printf "%s\n" "Starting systemd-cryptsetup@luks\x2dexample.service - Cryptography Setup for luks-example"' \
    '      printf "Please enter passphrase for disk luks-example:"' \
    '      duplicate_submitted=""' \
    '      IFS= read -r -t 0.3 duplicate_submitted || true' \
    '      [[ -n "$duplicate_submitted" ]] && : >"$TEST_DUPLICATE_SUBMISSION_MARKER"' \
    '    fi' \
    '    printf "\\nContinuing encrypted boot...\\n"' \
    '  done' \
    '  while :; do sleep 1; done' \
    'fi' \
    'printf "%s" "$TEST_CONSOLE_TRANSCRIPT"' \
    'submitted=""' \
    'IFS= read -r -t 3 submitted || true' \
    '[[ -n "$submitted" ]] && : >"$TEST_SUBMISSION_MARKER"' \
    >"$work_dir/bin/virsh"
  chmod 0755 "$work_dir/bin/virsh"
}

run_luks_console_gate() {
  local transcript=$1 marker=$2 event_log=$3 outcome submission event work_dir
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"

  TEST_CONSOLE_TRANSCRIPT=$transcript
  TEST_SUBMISSION_MARKER=$marker
  TEST_REQUIRE_TTY=0
  TEST_EXIT_EARLY=0
  TEST_PROMPT_TRIGGER=''
  TEST_SEQUENTIAL_PROMPTS=0
  TEST_DUPLICATE_FIRST_PROMPT=0
  TEST_PROGRESS_BEFORE_DUPLICATE=0
  TEST_POST_UNLOCK_PROGRESS=0
  TEST_ELLIPSIZED_CRYPTSETUP=0
  export TEST_CONSOLE_TRANSCRIPT TEST_SUBMISSION_MARKER TEST_REQUIRE_TTY TEST_EXIT_EARLY
  export TEST_PROMPT_TRIGGER TEST_SEQUENTIAL_PROMPTS TEST_DUPLICATE_FIRST_PROMPT
  export TEST_PROGRESS_BEFORE_DUPLICATE TEST_POST_UNLOCK_PROGRESS TEST_ELLIPSIZED_CRYPTSETUP
  rm -f -- "$marker" "$event_log"
  work_dir=$(dirname "$marker")
  write_virsh_console_fixture "$work_dir"

  if PATH="$work_dir/bin:$PATH" \
    hermes_luks_console_unlock fixture qemu:///test 1 "$event_log"; then
    outcome=unlocked
  else
    outcome=blocked
  fi
  if [[ -e "$marker" ]]; then
    submission=yes
  else
    submission=no
  fi
  event=missing
  if [[ -r "$event_log" ]]; then
    event=$(sed -n '$s/^[^ ]* //p' "$event_log")
  fi
  printf 'outcome=%s submission=%s event=%s\n' "$outcome" "$submission" "$event"
}

run_luks_console_early_exit() {
  local event_log=$1 outcome event work_dir
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
  rm -f -- "$event_log"
  work_dir=$(dirname "$event_log")
  write_virsh_console_fixture "$work_dir"
  TEST_EXIT_EARLY=1
  TEST_EXIT_TEXT='console connection refused'
  TEST_REQUIRE_TTY=0
  TEST_PROMPT_TRIGGER=''
  TEST_SEQUENTIAL_PROMPTS=0
  TEST_DUPLICATE_FIRST_PROMPT=0
  TEST_PROGRESS_BEFORE_DUPLICATE=0
  TEST_POST_UNLOCK_PROGRESS=0
  TEST_ELLIPSIZED_CRYPTSETUP=0
  export TEST_EXIT_EARLY TEST_EXIT_TEXT TEST_REQUIRE_TTY TEST_PROMPT_TRIGGER
  export TEST_SEQUENTIAL_PROMPTS TEST_DUPLICATE_FIRST_PROMPT
  export TEST_PROGRESS_BEFORE_DUPLICATE TEST_POST_UNLOCK_PROGRESS TEST_ELLIPSIZED_CRYPTSETUP

  if PATH="$work_dir/bin:$PATH" \
    hermes_luks_console_unlock fixture qemu:///test 1 "$event_log"; then
    outcome=unlocked
  else
    outcome=blocked
  fi
  event=missing
  if [[ -r "$event_log" ]]; then
    event=$(sed -n '$s/^[^ ]* //p' "$event_log")
  fi
  printf 'outcome=%s event=%s\n' "$outcome" "$event"
}

run_luks_console_tty_gate() {
  local work_dir=$1 event_log outcome submission event
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
  mkdir -p "$work_dir/bin"
  event_log="$work_dir/events"
  TEST_SUBMISSION_MARKER="$work_dir/submission"
  TEST_CONSOLE_TRANSCRIPT='Please enter passphrase for disk luks-example:'
  TEST_REQUIRE_TTY=1
  TEST_EXIT_EARLY=0
  TEST_PROMPT_TRIGGER=''
  TEST_SEQUENTIAL_PROMPTS=0
  TEST_DUPLICATE_FIRST_PROMPT=0
  TEST_PROGRESS_BEFORE_DUPLICATE=0
  TEST_POST_UNLOCK_PROGRESS=0
  TEST_ELLIPSIZED_CRYPTSETUP=0
  export TEST_SUBMISSION_MARKER TEST_CONSOLE_TRANSCRIPT TEST_REQUIRE_TTY TEST_EXIT_EARLY
  export TEST_PROMPT_TRIGGER TEST_SEQUENTIAL_PROMPTS TEST_DUPLICATE_FIRST_PROMPT
  export TEST_PROGRESS_BEFORE_DUPLICATE TEST_POST_UNLOCK_PROGRESS TEST_ELLIPSIZED_CRYPTSETUP
  write_virsh_console_fixture "$work_dir"

  if PATH="$work_dir/bin:$PATH" \
    hermes_luks_console_unlock fixture qemu:///test 2 "$event_log"; then
    outcome=unlocked
  else
    outcome=blocked
  fi
  if [[ -e "$TEST_SUBMISSION_MARKER" ]]; then
    submission=yes
  else
    submission=no
  fi
  event=missing
  if [[ -r "$event_log" ]]; then
    event=$(sed -n '$s/^[^ ]* //p' "$event_log")
  fi
  printf 'outcome=%s submission=%s event=%s\n' "$outcome" "$submission" "$event"
}

run_luks_console_preattached_gate() {
  local work_dir=$1 event_log ready_file trigger marker watcher_pid
  local outcome=blocked ready=no submission=no event=missing
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
  mkdir -p "$work_dir/bin"
  event_log="$work_dir/events"
  ready_file="$work_dir/ready"
  trigger="$work_dir/reboot-prompt"
  marker="$work_dir/submission"
  rm -f -- "$event_log" "$ready_file" "$trigger" "$marker"

  TEST_CONSOLE_TRANSCRIPT='Please enter passphrase for disk luks-example:'
  TEST_SUBMISSION_MARKER=$marker
  TEST_PROMPT_TRIGGER=$trigger
  TEST_REQUIRE_TTY=1
  TEST_EXIT_EARLY=0
  TEST_SEQUENTIAL_PROMPTS=0
  TEST_DUPLICATE_FIRST_PROMPT=0
  TEST_PROGRESS_BEFORE_DUPLICATE=0
  TEST_POST_UNLOCK_PROGRESS=0
  TEST_ELLIPSIZED_CRYPTSETUP=0
  export TEST_CONSOLE_TRANSCRIPT TEST_SUBMISSION_MARKER TEST_PROMPT_TRIGGER
  export TEST_REQUIRE_TTY TEST_EXIT_EARLY TEST_SEQUENTIAL_PROMPTS
  export TEST_DUPLICATE_FIRST_PROMPT TEST_PROGRESS_BEFORE_DUPLICATE
  export TEST_POST_UNLOCK_PROGRESS TEST_ELLIPSIZED_CRYPTSETUP
  write_virsh_console_fixture "$work_dir"

  PATH="$work_dir/bin:$PATH" \
    hermes_luks_console_unlock fixture qemu:///test 2 "$event_log" "$ready_file" &
  watcher_pid=$!
  for _ in {1..100}; do
    [[ -e "$ready_file" ]] && break
    kill -0 "$watcher_pid" 2>/dev/null || break
    sleep 0.01
  done
  if [[ -e "$ready_file" ]]; then
    ready=yes
    : >"$trigger"
  fi
  if wait "$watcher_pid"; then
    outcome=unlocked
  fi
  [[ -e "$marker" ]] && submission=yes
  if [[ -r "$event_log" ]]; then
    event=$(sed -n '$s/^[^ ]* //p' "$event_log")
  fi
  printf 'outcome=%s ready=%s submission=%s event=%s\n' \
    "$outcome" "$ready" "$submission" "$event"
}

run_luks_console_consecutive_boots() {
  local work_dir=$1 quiet_boot_boundary=${2:-0} post_unlock_progress=${3:-0}
  local in_place_status_repaint=${4:-0} ellipsized_cryptsetup=${5:-0}
  local event_log ready_file first_marker second_marker watcher_pid
  local first=no second=no events=0 boundaries=0
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
  mkdir -p "$work_dir/bin"
  event_log="$work_dir/events"
  ready_file="$work_dir/ready"
  first_marker="$work_dir/first-submission"
  second_marker="$work_dir/second-submission"
  rm -f -- "$event_log" "$ready_file" "$first_marker" "$second_marker"

  TEST_CONSOLE_TRANSCRIPT=''
  TEST_SUBMISSION_MARKER="$work_dir/unused-submission"
  TEST_PROMPT_TRIGGER=''
  TEST_FIRST_SUBMISSION_MARKER=$first_marker
  TEST_SECOND_SUBMISSION_MARKER=$second_marker
  TEST_SEQUENTIAL_PROMPTS=1
  TEST_REQUIRE_TTY=1
  TEST_EXIT_EARLY=0
  TEST_DUPLICATE_FIRST_PROMPT=0
  TEST_PROGRESS_BEFORE_DUPLICATE=0
  TEST_QUIET_BOOT_BOUNDARY=$quiet_boot_boundary
  TEST_POST_UNLOCK_PROGRESS=$post_unlock_progress
  TEST_IN_PLACE_STATUS_REPAINT=$in_place_status_repaint
  TEST_ELLIPSIZED_CRYPTSETUP=$ellipsized_cryptsetup
  export TEST_CONSOLE_TRANSCRIPT TEST_SUBMISSION_MARKER TEST_PROMPT_TRIGGER
  export TEST_FIRST_SUBMISSION_MARKER TEST_SECOND_SUBMISSION_MARKER
  export TEST_SEQUENTIAL_PROMPTS TEST_REQUIRE_TTY TEST_EXIT_EARLY
  export TEST_DUPLICATE_FIRST_PROMPT TEST_PROGRESS_BEFORE_DUPLICATE
  export TEST_QUIET_BOOT_BOUNDARY TEST_POST_UNLOCK_PROGRESS TEST_IN_PLACE_STATUS_REPAINT
  export TEST_ELLIPSIZED_CRYPTSETUP
  write_virsh_console_fixture "$work_dir"

  if declare -F hermes_luks_console_watch >/dev/null; then
    PATH="$work_dir/bin:$PATH" \
      hermes_luks_console_watch fixture qemu:///test 3 "$event_log" "$ready_file" &
  else
    PATH="$work_dir/bin:$PATH" \
      hermes_luks_console_unlock fixture qemu:///test 3 "$event_log" "$ready_file" &
  fi
  watcher_pid=$!
  for _ in {1..300}; do
    if [[ -e "$first_marker" && -e "$second_marker" ]]; then
      break
    fi
    kill -0 "$watcher_pid" 2>/dev/null || break
    sleep 0.01
  done
  [[ -e "$first_marker" ]] && first=yes
  [[ -e "$second_marker" ]] && second=yes
  kill "$watcher_pid" 2>/dev/null || true
  wait "$watcher_pid" 2>/dev/null || true
  if [[ -r "$event_log" ]]; then
    events=$(grep -c 'luks-prompt-verified input-submitted=1' "$event_log" || true)
    boundaries=$(grep -c 'luks-boot-boundary-observed input-submitted=0' "$event_log" || true)
  fi
  printf 'first=%s second=%s verified-events=%s boundaries=%s\n' \
    "$first" "$second" "$events" "$boundaries"
}

run_luks_console_duplicate_redraw() {
  local work_dir=$1 progress_before_duplicate=${2:-0}
  local event_log ready_file first_marker second_marker duplicate_marker watcher_pid
  local first=no second=no duplicate=no events=0
  # shellcheck source=../../vm/lib-hermes-luks-console.sh
  source "$PROJECT_ROOT/vm/lib-hermes-luks-console.sh"
  mkdir -p "$work_dir/bin"
  event_log="$work_dir/events"
  ready_file="$work_dir/ready"
  first_marker="$work_dir/first-submission"
  second_marker="$work_dir/second-submission"
  duplicate_marker="$work_dir/duplicate-submission"
  rm -f -- "$event_log" "$ready_file" "$first_marker" "$second_marker" "$duplicate_marker"

  TEST_CONSOLE_TRANSCRIPT=''
  TEST_SUBMISSION_MARKER="$work_dir/unused-submission"
  TEST_PROMPT_TRIGGER=''
  TEST_FIRST_SUBMISSION_MARKER=$first_marker
  TEST_SECOND_SUBMISSION_MARKER=$second_marker
  TEST_DUPLICATE_SUBMISSION_MARKER=$duplicate_marker
  TEST_DUPLICATE_FIRST_PROMPT=1
  TEST_PROGRESS_BEFORE_DUPLICATE=$progress_before_duplicate
  TEST_QUIET_BOOT_BOUNDARY=1
  TEST_POST_UNLOCK_PROGRESS=0
  TEST_ELLIPSIZED_CRYPTSETUP=0
  TEST_SEQUENTIAL_PROMPTS=1
  TEST_REQUIRE_TTY=1
  TEST_EXIT_EARLY=0
  export TEST_CONSOLE_TRANSCRIPT TEST_SUBMISSION_MARKER TEST_PROMPT_TRIGGER
  export TEST_FIRST_SUBMISSION_MARKER TEST_SECOND_SUBMISSION_MARKER
  export TEST_DUPLICATE_SUBMISSION_MARKER TEST_DUPLICATE_FIRST_PROMPT
  export TEST_PROGRESS_BEFORE_DUPLICATE TEST_QUIET_BOOT_BOUNDARY
  export TEST_POST_UNLOCK_PROGRESS TEST_ELLIPSIZED_CRYPTSETUP
  export TEST_SEQUENTIAL_PROMPTS TEST_REQUIRE_TTY TEST_EXIT_EARLY
  write_virsh_console_fixture "$work_dir"

  PATH="$work_dir/bin:$PATH" \
    hermes_luks_console_watch fixture qemu:///test 3 "$event_log" "$ready_file" &
  watcher_pid=$!
  for _ in {1..300}; do
    if [[ -e "$first_marker" && -e "$second_marker" ]]; then
      break
    fi
    kill -0 "$watcher_pid" 2>/dev/null || break
    sleep 0.01
  done
  [[ -e "$first_marker" ]] && first=yes
  [[ -e "$second_marker" ]] && second=yes
  [[ -e "$duplicate_marker" ]] && duplicate=yes
  kill "$watcher_pid" 2>/dev/null || true
  wait "$watcher_pid" 2>/dev/null || true
  if [[ -r "$event_log" ]]; then
    events=$(grep -c 'luks-prompt-verified input-submitted=1' "$event_log" || true)
  fi
  printf 'first=%s second=%s duplicate=%s verified-events=%s\n' \
    "$first" "$second" "$duplicate" "$events"
}

Describe "Hermes encrypted-console input gate"
It "never submits input while GRUB is editing an encrypted-root entry"
grub_transcript='GRUB version 2.12
set gfxpayload=keep
linux ($root)/vmlinuz root=/dev/mapper/vg_root-root rd.auto=1 rd.luks.uuid=luks-example
initrd ($root)/initramfs.img'
When call run_luks_console_gate "$grub_transcript" \
  "$SHELLSPEC_WORKDIR/grub-submission" "$SHELLSPEC_WORKDIR/grub-events"
The status should be success
The output should equal \
  "outcome=blocked submission=no event=luks-prompt-not-observed input-submitted=0"
End

It "submits once after the Fedora LUKS prompt is observed"
luks_transcript='Starting systemd-cryptsetup@luks.service
Please enter passphrase for disk luks-example:'
When call run_luks_console_gate "$luks_transcript" \
  "$SHELLSPEC_WORKDIR/luks-submission" "$SHELLSPEC_WORKDIR/luks-events"
The status should be success
The output should equal \
  "outcome=unlocked submission=yes event=luks-prompt-verified input-submitted=1"
End

It "fails cleanly when the console process exits before a prompt"
When call run_luks_console_early_exit "$SHELLSPEC_WORKDIR/early-exit-events"
The status should be success
The stdout should equal \
  "outcome=blocked event=luks-console-exited input-submitted=0 detail=console-connection-refused exit-code=1"
The stderr should equal ""
End

It "allocates a controlling TTY before connecting to the serial console"
When call run_luks_console_tty_gate "$SHELLSPEC_WORKDIR/tty-gate"
The status should be success
The output should equal \
  "outcome=unlocked submission=yes event=luks-prompt-verified input-submitted=1"
The stderr should equal ""
End

It "attaches before a reboot-time prompt can be emitted"
When call run_luks_console_preattached_gate "$SHELLSPEC_WORKDIR/preattached-gate"
The status should be success
The output should equal \
  "outcome=unlocked ready=yes submission=yes event=luks-prompt-verified input-submitted=1"
The stderr should equal ""
End


It "keeps one verified watcher across consecutive cryptsetup cycles"
When call run_luks_console_consecutive_boots "$SHELLSPEC_WORKDIR/consecutive-boots"
The status should be success
The output should equal "first=yes second=yes verified-events=2 boundaries=2"
The stderr should equal ""
End

It "recognizes Fedora cryptsetup starts after quiet-boot progress"
When call run_luks_console_consecutive_boots "$SHELLSPEC_WORKDIR/quiet-consecutive-boots" 1 1
The status should be success
The output should equal "first=yes second=yes verified-events=2 boundaries=2"
The stderr should equal ""
End

It "recognizes Fedora cryptsetup starts after an in-place status repaint"
When call run_luks_console_consecutive_boots "$SHELLSPEC_WORKDIR/repaint-consecutive-boots" 0 0 1
The status should be success
The output should equal "first=yes second=yes verified-events=2 boundaries=2"
The stderr should equal ""
End

It "recognizes Fedora's ANSI-colored ellipsized cryptsetup unit"
When call run_luks_console_consecutive_boots "$SHELLSPEC_WORKDIR/ellipsized-consecutive-boots" 0 0 0 1
The status should be success
The output should equal "first=yes second=yes verified-events=2 boundaries=2"
The stderr should equal ""
End

It "does not resubmit when one boot prompt is redrawn"
When call run_luks_console_duplicate_redraw "$SHELLSPEC_WORKDIR/duplicate-redraw"
The status should be success
The output should equal "first=yes second=yes duplicate=no verified-events=2"
The stderr should equal ""
End

It "does not rearm on a post-unlock path-units marker before a same-boot redraw"
When call run_luks_console_duplicate_redraw "$SHELLSPEC_WORKDIR/progress-redraw" 1
The status should be success
The output should equal "first=yes second=yes duplicate=no verified-events=2"
The stderr should equal ""
End
End
