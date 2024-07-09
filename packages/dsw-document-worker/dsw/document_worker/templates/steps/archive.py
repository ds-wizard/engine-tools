import tarfile
import zipfile

from ...documents import DocumentFile, FileFormats
from .base import Step, TMP_DIR, register_step


class ArchiveStep(Step):
    NAME = 'archive'

    OPTION_INPUT_FILE_TARGET = 'inputFileDst'

    OPTION_TYPE = 'type'
    OPTION_MODE = 'compression'
    OPTION_LEVEL = 'compressionLevel'
    OPTION_FORMAT = 'format'

    TYPE_ZIP = 'zip'
    TYPE_TAR = 'tar'

    MODE_NONE = 'none'
    MODE_GZIP = 'gzip'
    MODE_BZIP2 = 'bzip2'
    MODE_LZMA = 'lzma'

    FORMAT_USTAR = 'ustar'
    FORMAT_GNU = 'gnu'
    FORMAT_PAX = 'pax'

    MODES_ZIP = {
        MODE_NONE: zipfile.ZIP_STORED,
        MODE_GZIP: zipfile.ZIP_DEFLATED,
        MODE_BZIP2: zipfile.ZIP_BZIP2,
        MODE_LZMA: zipfile.ZIP_LZMA,
    }

    MODES_TAR = {
        MODE_NONE: '',
        MODE_GZIP: 'gz',
        MODE_BZIP2: 'bz2',
        MODE_LZMA: 'xz',
    }

    FORMATS_TAR = {
        FORMAT_USTAR: tarfile.USTAR_FORMAT,
        FORMAT_GNU: tarfile.GNU_FORMAT,
        FORMAT_PAX: tarfile.PAX_FORMAT,
    }

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.type = self._load_type()
        self.mode = options.get(self.OPTION_MODE, self.MODE_NONE)
        self.input_file_src = ''
        self.input_file_dst = options.get(self.OPTION_INPUT_FILE_TARGET, '')
        self.compression_level = self._get_compression_level()
        self._rectify_compression_level()
        self.format = ''
        if self.type == self.TYPE_TAR:
            self.format = options.get(self.OPTION_FORMAT, self.FORMAT_PAX)

    def _get_compression_level(self):
        level_str = self.options.get(self.OPTION_LEVEL, '9')  # type: str
        if level_str.isdigit():
            return int(level_str)
        return 0

    def _load_type(self) -> str:
        t = self.options.get(self.OPTION_TYPE, '')  # type: str
        if t.lower().strip() == self.TYPE_TAR:
            return self.TYPE_TAR
        return self.TYPE_ZIP

    def _rectify_compression_level(self):
        self.compression_level = max(self.compression_level, 0)
        self.compression_level = min(self.compression_level, 9)

        if self.mode == self.MODE_BZIP2 and self.compression_level == 0:
            self.compression_level = 1

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    @property
    def tar_format(self):
        if self.mode == self.MODE_GZIP:
            return FileFormats.TAR_GZIP
        if self.mode == self.MODE_BZIP2:
            return FileFormats.TAR_BZIP2
        if self.mode == self.MODE_LZMA:
            return FileFormats.TAR_LZMA
        return FileFormats.TAR

    def _create_zip(self) -> DocumentFile:
        compression = self.MODES_ZIP[self.mode]
        zip_file = TMP_DIR / 'result.zip'
        with zipfile.ZipFile(
                file=str(zip_file),
                mode='w',
                compression=compression,
                compresslevel=self.compression_level,
        ) as archive:
            archive.write(self.input_file_src, self.input_file_dst)
        data = zip_file.read_bytes()
        zip_file.unlink()
        return DocumentFile(
            file_format=FileFormats.ZIP,
            content=data,
        )

    def _create_tar(self) -> DocumentFile:
        compression = self.MODES_TAR[self.mode]
        tar_format = self.FORMATS_TAR[self.format]
        tar_file = TMP_DIR / 'result.tar'
        extra_opts = {}
        if compression in ('gz', 'bz2'):
            extra_opts['compresslevel'] = self.compression_level
        with tarfile.open(
            name=str(tar_file),
            mode=f'x:{compression}',
            format=tar_format,
            **extra_opts,
        ) as archive:
            archive.add(self.input_file_src, self.input_file_dst)
        data = tar_file.read_bytes()
        tar_file.unlink()
        return DocumentFile(
            file_format=self.tar_format,
            content=data,
        )

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        # (future) allow multiple files to be archived
        self.input_file_src = document.filename('document')
        if self.input_file_dst == '':
            self.input_file_dst = self.input_file_src
        tmp_file = TMP_DIR / self.input_file_src
        tmp_file.write_bytes(document.content)
        self.input_file_src = str(tmp_file)

        if self.type == self.TYPE_TAR:
            file = self._create_tar()
        else:
            file = self._create_zip()

        tmp_file.unlink()
        return file


register_step(ArchiveStep.NAME, ArchiveStep)
