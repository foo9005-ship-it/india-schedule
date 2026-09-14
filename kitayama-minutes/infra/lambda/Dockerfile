# AWS Lambda用コンテナイメージ。
# generate_minutes.py が unzip/zip コマンド(外部プロセス)に依存するため、
# 標準のzip/unzipパッケージを追加したLambdaベースイメージを使う。
#
# ビルド（リポジトリの kitayama-minutes/ をビルドコンテキストにする）:
#   cd kitayama-minutes
#   docker build -f infra/lambda/Dockerfile -t kitayama-minutes-lambda .

FROM public.ecr.aws/lambda/python:3.12

RUN dnf install -y zip unzip && dnf clean all

COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
