# Autonomous Research & Report Agent - Frontend

The frontend interface for the Autonomous Research & Report Agent, allowing users to submit research topics and view generated reports.

## Setup Instructions

### Option 1: Using a local web server

1. Make sure you have Python installed (for a simple HTTP server)
2. Navigate to the frontend directory:
   ```
   cd d:\Autonomous-Research-Report-Agent\frontend
   ```
3. Start a local web server:
   ```
   # Python 3
   python -m http.server 3000
   
   # Python 2
   python -m SimpleHTTPServer 3000
   ```
4. Open your browser and navigate to `http://localhost:3000`

### Option 2: Using a production server

For production deployment, you can use any static hosting service:

1. Upload the contents of this directory to your hosting provider
2. Update the `API_URL` in `app.js` to point to your backend API endpoint

## Features

- Submit new research topics with customizable parameters
- View the status of ongoing research tasks
- Browse and view generated research reports
- See detailed information about sources and citations

## Configuration

Edit the `app.js` file to modify the API URL:

```javascript
const API_URL = 'http://localhost:8000'; // Change to your API endpoint
```

## Technologies Used

- React for UI components
- Tailwind CSS for styling
- Axios for API requests
- Marked for Markdown rendering

## Project Structure

- `index.html` - Main HTML file with Tailwind CSS integration
- `app.js` - Main JavaScript application with React components
- No separate CSS file needed as we're using Tailwind's utility classes

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
