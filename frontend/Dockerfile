FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG NEXT_PUBLIC_INFERENCE_MODE=online
ARG NEXT_PUBLIC_APP_MODE=demo
ARG NEXT_PUBLIC_BACKEND_URL=http://backend:8000

# Next.js reads NEXT_PUBLIC_* during build and inlines values into the client bundle.
ENV NEXT_PUBLIC_INFERENCE_MODE=${NEXT_PUBLIC_INFERENCE_MODE}
ENV NEXT_PUBLIC_APP_MODE=${NEXT_PUBLIC_APP_MODE}
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
