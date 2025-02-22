const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const path = require('path'); // Importing path module

const app = express();
const PORT = 3001;

// In-memory user storage (for demonstration purposes)
let users = [];

app.use(bodyParser.urlencoded({ extended: true }));

// Use path to set up a proper static file serving
app.use(express.static(path.join(__dirname, 'my-app'))); // Serve static files from the 'public' folder

app.use(session({
    secret: 'secret', // Change this to a secret string
    resave: false,
    saveUninitialized: true
}));

// Render the login page (use path.join to handle file paths)
app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname + '/login.html')); // Safely join paths
});

// Render the register page (use path.join to handle file paths)
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname +'/registration.html')); // Safely join paths
});

// Handle the login form submission
app.post('/login', (req, res) => {
    const { email, password } = req.body;

    const user = users.find(user => user.email === email);
    if (user && user.password === password) {
        req.session.user = user; // Store the user in session
        res.redirect(__dirname + '/welcome');
    } else {
        res.send('Invalid credentials');
    }
});

// Handle the registration form submission
app.post('/register', (req, res) => {
    const { email, password } = req.body;

    // Check if the email is already taken
    const existingUser = users.find(user => user.email === email);
    if (existingUser) {
        return res.send('Email is already registered');
    }

    // Store the user with plain text password
    const newUser = { email, password };
    users.push(newUser);

    res.redirect(__dirname + '/login.html'); // Redirect to login page after successful registration
});

// Render the dashboard page for logged-in users
app.get('/welcome', (req, res) => {
    if (!req.session.user) {
        return res.redirect(__dirname + '/login.html');
    }

    res.send(`<h1>Welcome, ${req.session.user.email}!</h1><p><a href="/logout">Logout</a></p>`);
});

// Handle logout
app.get('/logout', (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            return res.redirect(__dirname + '/welcome.html');
        }

        res.redirect(__dirname + '/login.html');
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
