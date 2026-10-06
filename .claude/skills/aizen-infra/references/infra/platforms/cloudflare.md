# Cloudflare Public Domain Exposure Guide

> Aizen: tunnel tokens and API tokens are secret values — the owner types them into the secret store (`references/infra/secrets.md`). Pin `cloudflared` to a version or digest instead of `latest` (`deploy-and-rollback.md` §1). Creating tunnels or DNS records is A3; production DNS is A4.

This guide details how to securely expose containerized applications to the public Internet using Cloudflare Tunnel or Cloudflare DNS Proxied records.

---

## Method 1: Cloudflare Tunnel (Recommended - Zero Open Ports)

Cloudflare Tunnel creates an encrypted outbound-only connection between your VPS/Docker environment and the Cloudflare global network. No public IP or open firewall inbound ports (80/443) are required on the host.

### 1. Docker Compose Integration
Add the `cloudflared` service directly into your `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    image: ${IMAGE_NAME}:${IMAGE_TAG}
    restart: unless-stopped
    expose:
      - "3000"

  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - app
```

### 2. Tunnel Routing Configuration
In the Cloudflare Zero Trust Dashboard (or via Cloudflare API):
- Public Hostname: `app.yourdomain.com`
- Service: `http://app:3000` (resolves via internal Docker network).

---

## Method 2: Cloudflare DNS Proxy (Standard VPS IP Routing)

When using a standard VPS with open ports 80/443:

### 1. DNS Record Settings
- Type: `A` (or `CNAME`)
- Name: `app` (subdomain) or `@` (root)
- Target: `<Public VPS IPv4 Address>`
- Proxy Status: **Proxied (Orange Cloud ON)**

### 2. Cloudflare SSL/TLS Mode
- Set SSL/TLS encryption mode to **Full (Strict)**.
- Deploy a Cloudflare Origin CA certificate on the host reverse proxy (Nginx / Caddy / Traefik) to guarantee end-to-end encryption.

---

## Method 3: Automation via Cloudflare MCP

When the `cloudflare-api` MCP server is registered in your agent environment:
1. Search available DNS zones:
   - Call MCP tool `search` with query `zones`.
2. Create or update DNS record:
   - Call MCP tool `execute` passing:
     ```json
     {
       "path": "/zones/{zone_id}/dns_records",
       "method": "POST",
       "body": {
         "type": "A",
         "name": "app.yourdomain.com",
         "content": "123.45.67.89",
         "ttl": 1,
         "proxied": true
       }
     }
     ```
