FROM public.ecr.aws/lambda/python:3.14

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

COPY src ${LAMBDA_TASK_ROOT}/src
COPY src/file_embedding_worker.py ${LAMBDA_TASK_ROOT}/worker.py

CMD ["worker.handler"]