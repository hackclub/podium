# Custom Mathesar image with Doppler CLI and auto-bootstrap
# Extends official image, adds Doppler for secrets, runs bootstrap on first start

# Pin to specific version for reproducibility
# Check https://hub.docker.com/r/mathesar/mathesar/tags for latest stable
FROM mathesar/mathesar:0.2.2

# Install Doppler CLI (Debian/Ubuntu base)
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler && \
    rm -rf /var/lib/apt/lists/*

# Copy bootstrap script
COPY bootstrap.py /code/bootstrap.py

# Copy custom entrypoint that runs bootstrap then starts Mathesar
COPY entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

# Doppler injects secrets, entrypoint handles bootstrap + startup
ENTRYPOINT ["doppler", "run", "--"]
CMD ["/code/entrypoint.sh"]
