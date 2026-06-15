FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY frontend/ .

RUN mkdir -p /output

CMD ["npm", "run", "dev"]
