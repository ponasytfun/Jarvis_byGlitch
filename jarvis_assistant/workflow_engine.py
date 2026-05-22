from __future__ import annotations

import time

from jarvis_assistant.actions import ActionExecutor
from jarvis_assistant.models import JarvisConfig, WorkflowResult


class WorkflowEngine:
    def __init__(self, action_executor: ActionExecutor, logger) -> None:
        self.action_executor = action_executor
        self.logger = logger.getChild("workflow_engine")

    def run_workflow(
        self,
        workflow_name: str,
        config: JarvisConfig,
        on_step_change=None,
    ) -> WorkflowResult:
        workflow = config.workflows.get(workflow_name)
        if workflow is None:
            message = f"Workflow '{workflow_name}' is not defined."
            self.logger.error(message)
            return WorkflowResult(success=False, message=message)

        if on_step_change is not None:
            on_step_change("Workflow Armed", f"Preparing {workflow_name}.")
        self.logger.info("Workflow start: %s", workflow_name)
        for index, step in enumerate(workflow.steps, start=1):
            step_title, step_detail = self._describe_step(step)
            if on_step_change is not None:
                on_step_change(
                    step_title,
                    f"{step_detail} ({index}/{len(workflow.steps)})",
                )
            self.logger.info(
                "Workflow step %s/%s: %s",
                index,
                len(workflow.steps),
                step.action,
            )
            step_success = False

            for attempt in range(1, max(1, step.retries) + 1):
                try:
                    self.action_executor.execute(
                        action_name=step.action,
                        params=step.params,
                        config=config,
                        dry_run=config.runtime.dry_run,
                        timeout_ms=step.timeout_ms,
                    )
                    step_success = True
                    break
                except Exception as exc:
                    if attempt < max(1, step.retries):
                        self.logger.warning(
                            "Step '%s' attempt %s/%s failed: %s",
                            step.action,
                            attempt,
                            step.retries,
                            exc,
                        )
                        time.sleep(0.5)
                    else:
                        self.logger.exception(
                            "Step '%s' failed permanently: %s",
                            step.action,
                            exc,
                        )

            if not step_success:
                if step.continue_on_error:
                    self.logger.warning(
                        "Continuing after failed step '%s' because continue_on_error is true.",
                        step.action,
                    )
                    if on_step_change is not None:
                        on_step_change(
                            "Continuing With Warning",
                            f"{step_title} reported an issue but the workflow is continuing.",
                        )
                else:
                    message = f"Workflow '{workflow_name}' failed on action '{step.action}'."
                    self.logger.error(message)
                    if on_step_change is not None:
                        on_step_change("Workflow Interrupted", message)
                    return WorkflowResult(success=False, message=message)

            if step.delay_after_ms > 0:
                self.logger.info("Step delay: %s ms", step.delay_after_ms)
                if not config.runtime.dry_run:
                    time.sleep(step.delay_after_ms / 1000.0)

        message = f"Workflow '{workflow_name}' completed successfully."
        self.logger.info(message)
        if on_step_change is not None:
            on_step_change("Workflow Complete", message)
        return WorkflowResult(success=True, message=message)

    def _describe_step(self, step) -> tuple[str, str]:
        action = step.action
        params = step.params or {}
        if action == "open_music_in_brave":
            return "Opening Music", "Opening YouTube Music and attempting playback."
        if action == "open_url_in_brave":
            return "Opening Brave", "Launching Brave with the requested URL."
        if action == "focus_or_launch_app":
            target = str(params.get("target", "application")).strip().title()
            return f"Focusing {target}", f"Finding or launching {target}."
        if action == "minimize_window":
            target = str(params.get("target", "window")).strip().title()
            return f"Minimizing {target}", f"Minimizing the {target} window."
        if action == "arrange_two_windows_side_by_side":
            left_target = str(params.get("left_target", "left window")).strip().title()
            right_target = str(params.get("right_target", "right window")).strip().title()
            return "Tiling Workspace", f"Arranging {left_target} and {right_target} side by side."
        if action == "wait":
            return "Stabilizing", "Waiting for the desktop to settle."
        if action == "show_notification":
            return "Posting Status", "Displaying a workflow notification."
        if action == "send_media_play_pause":
            return "Prompting Playback", "Sending a media play or pause command."
        if action == "send_keypress_to_window":
            return "Sending Shortcut", "Sending a safe shortcut to the focused window."
        return "Executing Step", action
