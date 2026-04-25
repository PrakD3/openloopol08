FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build Next.js app
# Note: Ensure NEXT_PUBLIC_BACKEND_URL is set during build or use client-side env
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

RUN npm run build

# Expose Next.js port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
