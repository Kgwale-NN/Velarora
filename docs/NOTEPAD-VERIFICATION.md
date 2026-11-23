# Notepad detection checks

Screenshots alone can confuse a white dashboard, an image of an app, and an
actual application window. A confidence score is a model prediction, not proof
that a Windows application is running.

For the `Notepad` class, Velarora now requires fresh Windows confirmation before
drawing boxes, saving a detection hit, sending a notification or raising a visual
alarm. Other model classes keep their existing visual behaviour.

- When capturing the Windows server itself, inspect that PC's processes.
- For another PC, use that PC's authenticated workstation heartbeat. The updated
  agent sends only the supported `notepad.exe` presence flag, not a full process list.
- Evidence expires after five seconds. Unknown or expired evidence cannot
  confirm a Notepad detection. A legacy agent reporting foreground
  `notepad.exe` supplies positive evidence; update its agent to support Notepad
  on another connected screen as well.
- The home server's process list must never be used for a remote PC.
- Once raised, an alarm remains latched until its teacher stops it. Closing
  Notepad does not replace the teacher's stop command.

This checks application presence, not every possible form of cheating, and it
does not make the underlying visual model infallible. A running Notepad process
alone does not fabricate an AI box: the model must also detect the window.

## Validate a model change

Use separate captured examples with Notepad open and closed, including small and
large windows, different positions, the dashboard, and connected-screen layouts.
Check localisation as well as class names. Deduplicate captures before splitting
data and keep captures from the same screen journey together.

Do not activate a checkpoint on its training score alone. Measure missed real
windows and false detections on separate examples. Keep the previous weights
available for rollback. Private screenshots, training sets and weights belong
under ignored `data/` paths rather than GitHub.

For a live regression check, replay a previously reported false screen with
Windows-confirmed absence; it must create no boxes, detection hits, notifications
or alarms. Then capture actual open Notepad, verify the visual alarm, stop it as
the owning teacher, close the test window, and repeat the negative check.
