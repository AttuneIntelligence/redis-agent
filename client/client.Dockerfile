################################
### REDIS AGENT CLIENT IMAGE ###
################################

FROM node:18-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

### EXPOSE PORT 3000
EXPOSE 3000

### RUN THE BUILD PROCESS
RUN npm run build

### START THE APPLICATION
CMD ["npm", "start"]

##########################
##########################