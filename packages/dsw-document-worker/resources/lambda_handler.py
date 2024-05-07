print('Loading lambda_handler')


def handler(event, context):
    try:
        print('LAMBDA> Starting handler')

        print('LAMBDA> Importing lambda_handler from dsw.document_worker')
        from dsw.document_worker import lambda_handler

        print('LAMBDA> Calling lambda_handler')
        lambda_handler(event, context)
    except Exception as e:
        print('LAMBDA> An error occurred: ' + str(e))
