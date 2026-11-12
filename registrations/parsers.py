from io import BytesIO
from django.core.files.uploadhandler import FileUploadHandler
from rest_framework.exceptions import APIException
from rest_framework.parsers import JSONParser, MultiPartParser


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = 'Submission payload exceeds the supported size.'


class BoundedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = stream.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise PayloadTooLarge()
        return super().parse(BytesIO(data), media_type, parser_context)


class UploadByteLimit(FileUploadHandler):
    def __init__(self, request):
        super().__init__(request)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > 20 * 1024 * 1024:
            raise PayloadTooLarge()
        return raw_data

    def file_complete(self, file_size):
        return None


class BoundedMultipartParser(MultiPartParser):
    # The global first upload handler also covers native Django/CSRF parsing.
    pass
