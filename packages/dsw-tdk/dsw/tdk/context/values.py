"""Reply values of value questions that are valid against the question's validations."""
from __future__ import annotations

import datetime
import re
import typing

from dsw.models.knowledge_model import common as v


if typing.TYPE_CHECKING:
    import random

    from dsw.models.knowledge_model import flat


ORCID = '0000-0002-1825-0097'
DOI = '10.5281/zenodo.1234567'  # cspell:disable-line
#: candidates tried in order for a regex validation
REGEX_CANDIDATES = ('123456', '12345678', 'abcdef', 'ABCDEF', 'abc123', 'jane.doe@example.org',
                    'https://example.org/', '2025-01-01', ORCID, DOI, '')

WORDS = ('data', 'project', 'research', 'archive', 'sample', 'survey', 'model', 'climate',
         'protein', 'dataset', 'analysis', 'repository', 'license', 'workflow', 'storage')
#: long, unicode, right-to-left and markup-like strings of the `edge` profile
# cspell:disable  # noqa: ERA001
EDGE_STRINGS = ('', 'x' * 2000, 'Žluťoučký kůň úpěl ďábelské ódy 😀', 'مشروع البيانات',
                '<script>alert(1)</script> & </div>', '{{ ctx }} {% raw %} | pipe',
                'line\nbreak\ttab',
                ' surrounding spaces ', '**markdown** _emphasis_ [link](https://example.org)')
# cspell:enable  # noqa: ERA001


class ValueGenerator:
    """Values by value type, satisfying MinLength/MaxLength, Min/MaxNumber, From/To Date,
    DateTime and Time, ORCID, DOI, Domain and (when a candidate matches) Regex validations."""

    def __init__(self, rng: random.Random, strings: str, now: datetime.datetime):
        self.rng = rng
        self.strings = strings
        self.now = now

    def text(self, words: int = 3) -> str:
        if self.strings == 'edge':
            return self.rng.choice(EDGE_STRINGS) or 'x'
        count = 1 if self.strings == 'short' else words
        return ' '.join(self.rng.choice(WORDS) for _ in range(count)).capitalize()

    def value(self, question: flat.ValueQuestion) -> str | None:
        """A valid value, or None when no valid one could be made (an unsatisfiable regex)."""
        rules = {type(rule): rule for rule in question.validations}
        if v.OrcidQuestionValidation in rules:
            return ORCID
        if v.DoiQuestionValidation in rules:
            return DOI
        if v.RegexQuestionValidation in rules:
            pattern = str(getattr(rules[v.RegexQuestionValidation], 'value', ''))
            return next((c for c in REGEX_CANDIDATES if _matches(pattern, c)), None)
        value_type = question.value_type
        generate = getattr(self, f'_{value_type.removesuffix("QuestionValueType").lower()}')
        return generate(rules)

    def _boundary(self) -> bool:
        return self.strings == 'edge'

    def _string(self, rules: dict) -> str:
        minimum = getattr(rules.get(v.MinLengthQuestionValidation), 'value', 0)
        maximum = getattr(rules.get(v.MaxLengthQuestionValidation), 'value', None)
        text = self.text()
        if self._boundary() and maximum is not None:
            text = 'x' * maximum
        elif self._boundary() and minimum:
            text = 'x' * minimum
        if maximum is not None:
            text = text[:maximum]
        return text + 'x' * max(0, minimum - len(text))

    _text = _string

    def _number(self, rules: dict) -> str:
        minimum = getattr(rules.get(v.MinNumberQuestionValidation), 'value', 0)
        maximum = getattr(rules.get(v.MaxNumberQuestionValidation), 'value', minimum + 1000)
        if self._boundary():
            number = self.rng.choice((minimum, maximum))
        else:
            number = self.rng.randint(int(minimum), int(max(minimum, maximum)))
        return str(int(number)) if float(number).is_integer() else str(number)

    def _date(self, rules: dict) -> str:
        return self._between(rules, v.FromDateQuestionValidation, v.ToDateQuestionValidation,
                             lambda d: d.date().isoformat(), _parse_date)

    def _datetime(self, rules: dict) -> str:
        return self._between(rules, v.FromDateTimeQuestionValidation,
                             v.ToDateTimeQuestionValidation,
                             lambda d: d.strftime('%Y-%m-%dT%H:%M:%SZ'), _parse_datetime)

    def _time(self, rules: dict) -> str:
        return self._between(rules, v.FromTimeQuestionValidation, v.ToTimeQuestionValidation,
                             lambda d: d.strftime('%H:%M'), _parse_time)

    def _between(self, rules: dict, low_rule: type, high_rule: type, render, parse) -> str:
        low = parse(rules[low_rule].value) if low_rule in rules else self.now - _DAYS_400
        high = parse(rules[high_rule].value) if high_rule in rules else max(low, self.now)
        if self._boundary():
            return render(self.rng.choice((low, high)))
        span = max(0, int((high - low).total_seconds()))
        return render(low + datetime.timedelta(seconds=self.rng.randint(0, span) // 60 * 60))

    def _email(self, rules: dict) -> str:
        return f'{self.rng.choice(WORDS)}.{self.rng.choice(WORDS)}@example.org'

    def _url(self, rules: dict) -> str:
        domain = getattr(rules.get(v.DomainQuestionValidation), 'value', 'example.org')
        return f'https://{domain}/{self.rng.choice(WORDS)}'

    def _color(self, rules: dict) -> str:
        return f'#{self.rng.randrange(0x1000000):06x}'


_DAYS_400 = datetime.timedelta(days=400)


def _matches(pattern: str, candidate: str) -> bool:
    try:
        return re.fullmatch(pattern, candidate) is not None
    except re.error:
        return False


def _parse_date(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text[:10]).replace(tzinfo=datetime.UTC)


def _parse_datetime(text: str) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.UTC)


def _parse_time(text: str) -> datetime.datetime:
    hours, minutes = (int(part) for part in text.split(':')[:2])
    return datetime.datetime(2025, 1, 1, hours, minutes, tzinfo=datetime.UTC)
