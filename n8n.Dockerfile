FROM n8nio/n8n:latest

USER root

# Optional: Install any additional tools needed for your agents
RUN apk add --no-cache curl

USER node
