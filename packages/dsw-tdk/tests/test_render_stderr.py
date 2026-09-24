import os

from dsw.tdk.render import filtered_native_stderr


NOISE = (
    b'Fontconfig error: the ambiguous constant name: normal: '
    b'Use :<property name>=<keyword> instead of :<keyword>\n'
    b'Fontconfig warning: "memory", line 3: invalid constant used : normal\n'
)


def test_fontconfig_noise_is_dropped(capfd):
    with filtered_native_stderr():
        os.write(2, NOISE * 3)
    assert capfd.readouterr().err == ''


def test_other_native_output_is_kept(capfd):
    with filtered_native_stderr():
        os.write(2, NOISE + b'Fontconfig error: something else\nreal problem\n' + NOISE)
    assert capfd.readouterr().err == 'Fontconfig error: something else\nreal problem\n'


def test_stderr_is_restored_after_an_error(capfd):
    try:
        with filtered_native_stderr():
            os.write(2, b'before failure\n')
            raise RuntimeError('boom')
    except RuntimeError:
        pass
    os.write(2, b'after\n')
    assert capfd.readouterr().err == 'before failure\nafter\n'
