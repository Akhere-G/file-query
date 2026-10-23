
# Build Antiword
FROM public.ecr.aws/lambda/python:3.14 AS antiword-builder

RUN dnf install -y gcc make git \
  && dnf clean all

WORKDIR /tmp/antiword

RUN git clone --depth 1 https://github.com/grobian/antiword.git . \
  && make -f Makefile.Linux \
  && install -D -m 755 antiword /opt/antiword/bin/antiword \
  && mkdir -p /opt/antiword/share/antiword \
  && cp Resources/*.txt /opt/antiword/share/antiword/ \
  && cp Resources/fontnames /opt/antiword/share/antiword/

# Lambda runtime
FROM public.ecr.aws/lambda/python:3.14

COPY --from=antiword-builder /opt/antiword/bin/antiword /usr/local/bin/antiword
COPY --from=antiword-builder /opt/antiword/share/antiword/ /usr/share/antiword/

COPY requirements.txt requirements.lambda.txt ${LAMBDA_TASK_ROOT}/

RUN pip install --no-cache-dir -r requirements.txt -r requirements.lambda.txt \
  && command -v antiword

COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY src/file_embedding_worker.py ${LAMBDA_TASK_ROOT}/worker.py

CMD ["worker.handler"]
