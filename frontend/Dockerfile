FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install -g @vue/cli
RUN npm install @vue/cli-service --save-dev
RUN rm -rf node_modules
RUN npm install
RUN npm cache clean -f

COPY . .

EXPOSE 8080

CMD ["npm", "run", "serve"]