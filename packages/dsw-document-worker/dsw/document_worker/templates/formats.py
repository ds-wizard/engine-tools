from ..consts import FormatField, StepField
from ..context import Context
from ..documents import DocumentFile
from ..templates.steps import create_step, Step, \
    FormatStepException, WkHtmlToPdfStep


class Format:

    FORMAT_META_REQUIRED = [FormatField.UUID,
                            FormatField.NAME,
                            FormatField.STEPS]

    STEP_META_REQUIRED = [StepField.NAME,
                          StepField.OPTIONS]

    def __init__(self, template, metadata: dict):
        self.template = template
        self._verify_metadata(metadata)
        self.uuid = self._trace = metadata[FormatField.UUID]
        self.name = metadata[FormatField.NAME]
        Context.logger.info(f'Setting up format "{self.name}" ({self._trace})')
        self.steps = self._create_steps(metadata)
        if len(self.steps) < 1:
            self.template.raise_exc(f'Format {self.name} has no steps')

    def _verify_metadata(self, metadata: dict):
        for required_field in self.FORMAT_META_REQUIRED:
            if required_field not in metadata:
                self.template.raise_exc(f'Missing required field {required_field} for format')
        for step in metadata[FormatField.STEPS]:
            for required_field in self.STEP_META_REQUIRED:
                if required_field not in step:
                    self.template.raise_exc(f'Missing required field {required_field} '
                                            f'for step in format "{self.name}"')

    def _create_steps(self, metadata: dict) -> list[Step]:
        steps = []
        for step_meta in metadata[FormatField.STEPS]:
            step_name = step_meta[StepField.NAME]
            step_options = step_meta[StepField.OPTIONS]
            try:
                steps.append(
                    create_step(self.template, step_name, step_options)
                )
            except FormatStepException as e:
                Context.logger.warning('Handling job exception', exc_info=True)
                self.template.raise_exc(f'Cannot load step "{step_name}" of format "{self.name}"\n'
                                        f'- {e.message}')
            except Exception as e:
                Context.logger.warning('Handling job exception', exc_info=True)
                self.template.raise_exc(f'Cannot load step "{step_name}" of format "{self.name}"\n'
                                        f'- {str(e)}')
        return steps

    @property
    def is_pdf(self) -> bool:
        # TODO: refactor to check output FileFormat for step (instead of specific step)
        return isinstance(self.steps[-1], WkHtmlToPdfStep)

    def requires_via_extras(self, requirement: str) -> bool:
        return any(step.requires_via_extras(requirement)
                   for step in self.steps)

    def execute(self, context: dict) -> DocumentFile:
        result = self.steps[0].execute_first(context)
        for step in self.steps[1:]:
            if result is not None:
                result = step.execute_follow(result)
            else:
                break
        return result
