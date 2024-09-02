FROM docker.io/python:3.12.5-bookworm

RUN addgroup app
RUN adduser app --ingroup app
USER app
ENV PATH="/home/app/.local/bin:${PATH}"

WORKDIR /app
COPY --chown=app:app . .

RUN pip3 install --user .

ENV ROOT_PATH="/app"
EXPOSE 5000

CMD ["testing-websockets-chat-server"]
