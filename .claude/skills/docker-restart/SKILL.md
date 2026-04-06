# Docker Restart Skill
1. Run `docker compose down` in the project directory
2. Run `docker compose build --no-cache`
3. Run `docker compose up -d`
4. Wait 5 seconds, then run `docker compose logs --tail=20`
5. Report container status and any errors
