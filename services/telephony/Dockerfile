FROM node:20-alpine
WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN npm install -g pnpm@9 && pnpm install --frozen-lockfile || pnpm install

COPY tsconfig.json ./
COPY src ./src
RUN pnpm build

EXPOSE 8005
CMD ["node", "dist/server.js"]
