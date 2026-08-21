#!/bin/bash
# 服务器更新脚本:从 GitHub 拉取最新代码并重启服务
set -e
cd /opt/sc-link
git pull origin main
docker compose -f deploy/docker-compose.prod.yml up -d --build
echo "SC-Link 已更新并重启"
