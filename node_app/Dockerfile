# Use the Node.js LTS version as the base image
FROM node:20.10.0-alpine

# Set the working directory inside the container
WORKDIR /node_app

# Copy package.json and package-lock.json to the working directory
COPY package.json package-lock.json ./

# Install the application dependencies
RUN npm install

# Copy all application files to the container
COPY . .

# Expose the port that the application runs on 
EXPOSE 3000

# Command to start the application
CMD ["node", "app.js"]