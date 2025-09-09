#!/usr/bin/env node
import React, { useState, useEffect } from "react";
import { render, Text, Box } from "ink";  // Part 1F: Ink components for terminal UI
import SelectInput from "ink-select-input";  // Part 1F: Menu with arrow keys
import Spinner from "ink-spinner";  // Part 1G: Loading spinner
import open from "open";  // Part 1G: Opens browser
import fetch from "node-fetch";  // Part 1G: HTTP requests
import { v4 as uuidv4 } from "uuid";  // Part 1G: Generate unique tokens
import { saveAuth, loadAuth, clearAuth, getConfigPath } from "./config.js";  // Part 1H: Token persistence

// Main CLI Component
const App = () => {
  // Part 1F: Track which screen we're on
  const [screen, setScreen] = useState<"menu" | "login" | "secrets" | "logout">("menu");
  
  // Part 1G: Store user info and JWT token
  const [user, setUser] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loginStatus, setLoginStatus] = useState<
    "idle" | "opening" | "polling" | "success" | "error"
  >("idle");
  const [pollCount, setPollCount] = useState(0);

  // Phase 1H: Load saved auth on startup
  useEffect(() => {
    const savedAuth = loadAuth();
    if (savedAuth.token && savedAuth.user) {
      setToken(savedAuth.token);
      setUser(savedAuth.user);
      console.log(`Welcome back, ${savedAuth.user.name || savedAuth.user.login}!`);
    }
    // Show where config is stored (for debugging)
    console.log(`Config stored at: ${getConfigPath()}`);
  }, []); // Run once on startup

  // 2. Menu options (key added to prevent React warning)
  const menuItems = user ? [
    { label: "Logout", value: "logout", key: "logout" },
    { label: "View Secrets", value: "secrets", key: "secrets" },
    { label: "Exit", value: "exit", key: "exit" },
  ] : [
    { label: "Login with GitHub", value: "login", key: "login" },
    { label: "View Secrets", value: "secrets", key: "secrets" },
    { label: "Exit", value: "exit", key: "exit" },
  ];

  // 3. Handle menu selection
  const handleSelect = (item: any) => {
    if (item.value === "exit") {
      process.exit(0);
    } else if (item.value === "login") {
      setScreen("login");
      startOAuthFlow(); // Phase 1G: Start OAuth when login selected
    } else if (item.value === "logout") {
      // Show logout screen briefly
      setScreen("logout");
      // Clear user session
      setUser(null);
      setToken(null);
      setLoginStatus("idle");
      setPollCount(0);
      // Phase 1H: Clear saved auth from disk
      clearAuth();
      // Return to menu after 1 second
      setTimeout(() => setScreen("menu"), 1000);
    } else if (item.value === "secrets") {
      setScreen("secrets");
    }
  };

  // 4. Phase 1G: OAuth Flow Functions
  const startOAuthFlow = async () => {
    try {
      // Reset state for new login
      setLoginStatus("idle");
      setPollCount(0);
      
      // 4a. Generate unique CLI token
      const cliToken = uuidv4();
      setLoginStatus("opening");

      // 4b. Open browser to start OAuth
      const authUrl = `http://localhost:8001/auth/github/start?cli_token=${cliToken}`;
      await open(authUrl);

      // 4c. Start polling for token
      setLoginStatus("polling");
      pollForToken(cliToken);
    } catch (error) {
      setLoginStatus("error");
      console.error("Failed to start OAuth:", error);
    }
  };

  const pollForToken = async (cliToken: string, attempts = 0) => {
    // 5. Poll backend for token (max 60 attempts = 2 minutes)
    if (attempts >= 60) {
      setLoginStatus("error");
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8001/auth/cli-exchange?cli_token=${cliToken}`
      );

      if (response.ok) {
        // 5a. Success! Got the token
        const data = (await response.json()) as { token: string; user: any };
        setUser(data.user);
        setToken(data.token);
        setLoginStatus("success");
        
        // Phase 1H: Save auth to disk
        saveAuth(data.token, data.user);

        // 5b. Go back to menu after 2 seconds
        setTimeout(() => setScreen("menu"), 2000);
      } else {
        // 5c. Not ready yet, poll again in 2 seconds
        setPollCount(attempts + 1);
        setTimeout(() => pollForToken(cliToken, attempts + 1), 2000);
      }
    } catch (error) {
      setLoginStatus("error");
      console.error("Polling error:", error);
    }
  };

  // 6. Render different screens
  if (screen === "menu") {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          🔐 Secret Sharing CLI
        </Text>
        {user && (
          <Text color="green">Logged in as: {user.name || user.login}</Text>
        )}
        <Text> </Text>
        <Text>Choose an option:</Text>
        <SelectInput items={menuItems} onSelect={handleSelect} />
      </Box>
    );
  }

  if (screen === "login") {
    // Phase 1G: Show login status
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          🔐 GitHub Login
        </Text>
        <Text> </Text>

        {loginStatus === "opening" && (
          <Text color="yellow">
            <Spinner type="dots" /> Opening browser...
          </Text>
        )}

        {loginStatus === "polling" && (
          <Box flexDirection="column">
            <Text color="yellow">
              <Spinner type="dots" /> Waiting for login... (attempt {pollCount}
              /60)
            </Text>
            <Text color="gray">Please complete login in your browser</Text>
          </Box>
        )}

        {loginStatus === "success" && (
          <Box flexDirection="column">
            <Text color="green">✅ Login successful!</Text>
            <Text>Welcome, {user?.name || user?.login}!</Text>
            <Text color="gray">Returning to menu...</Text>
          </Box>
        )}

        {loginStatus === "error" && (
          <Box flexDirection="column">
            <Text color="red">❌ Login failed</Text>
            <Text>Please try again or press Ctrl+C to exit</Text>
          </Box>
        )}
      </Box>
    );
  }

  if (screen === "secrets") {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          📝 Your Secrets
        </Text>
        <Text> </Text>
        {user ? (
          <Box flexDirection="column">
            <Text color="green">Logged in as: {user.name || user.login}</Text>
            <Text>Token: {token?.substring(0, 20)}...</Text>
            <Text> </Text>
            <Text color="gray">Secret management coming in Phase 2!</Text>
          </Box>
        ) : (
          <Text color="yellow">Please login first!</Text>
        )}
        <Text> </Text>
        <Text color="gray">Press Ctrl+C to return to menu</Text>
      </Box>
    );
  }

  if (screen === "logout") {
    return (
      <Box flexDirection="column">
        <Text color="yellow">👋 Logging out...</Text>
        <Text color="gray">Returning to menu...</Text>
      </Box>
    );
  }

  return null;
};

// 7. Check if we're in a TTY before rendering
if (!process.stdin.isTTY) {
  console.log('This CLI requires an interactive terminal (TTY).');
  console.log('Please run directly in a terminal, not through pipes or scripts.');
  process.exit(1);
}

// 8. Render the app
render(<App />);
