FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY design_system /design_system
COPY frontend/ .

RUN mkdir -p /output

CMD ["npm", "run", "dev"]
