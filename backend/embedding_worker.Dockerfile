FROM public.ecr.aws/lambda/python:3.14

# antiword extracts text from legacy .doc files (see extract_doc).
RUN dnf install -y antiword && dnf clean all && command -v antiword

COPY requirements.txt requirements.lambda.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt -r requirements.lambda.txt

COPY src ${LAMBDA_TASK_ROOT}/src
COPY src/file_embedding_worker.py ${LAMBDA_TASK_ROOT}/worker.py

CMD ["worker.handler"]
