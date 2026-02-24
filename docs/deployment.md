# Deployment Guide

## Recommended Targets
- AWS ECS or EKS
- Render / Railway

## Database Setup
- Use managed Postgres with automated backups.
- Configure separate databases for `indus` and `merchant`.

## Hyperswitch Setup
- Create and configure connectors in Hyperswitch.
- Generate API keys and set them in the payments service.

## Environment Variables
- Copy `.env.example` for each service and set production values.
- Ensure `PAYMENTS_SERVICE_URL` is set for Indus and Merchant.

## Observability
- Set `LOG_LEVEL=INFO` or `DEBUG` for troubleshooting.
- Add metrics and tracing in production as needed.
