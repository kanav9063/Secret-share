#!/usr/bin/env node
import React, { useState, useEffect } from "react";
import { render, Text, Box, useInput, useApp } from "ink"; // Part 1F: Ink components for terminal UI
import SelectInput from "ink-select-input"; // Part 1F: Menu with arrow keys
import Spinner from "ink-spinner"; // Part 1G: Loading spinner
import TextInput from "ink-text-input"; // Part 2E: Text input for creating secrets
import open from "open"; // Part 1G: Opens browser
import fetch from "node-fetch"; // Part 1G: HTTP requests
import { v4 as uuidv4 } from "uuid"; // Part 1G: Generate unique tokens
import { saveAuth, loadAuth, clearAuth, getConfigPath } from "./config.js"; // Part 1H: Token persistence

// Phase 2E: TypeScript interface for our secret data
interface Secret {
  id: number;
  key: string;
  value: string;
  created_by_id: number;
  created_at: string;
  can_write: boolean;
}

// Phase 2E: Secrets Screen Component
// This component shows all secrets and lets users create new ones
const SecretsScreen = ({
  token,
  onBack,
}: {
  token: string | null;
  onBack: () => void;
}) => {
  // 1. State to track our secrets and UI mode
  const [secrets, setSecrets] = useState<Secret[]>([]); // List of secrets from backend
  const [loading, setLoading] = useState(true); // Are we loading data?
  const [error, setError] = useState<string | null>(null); // Any errors to show?
  const [mode, setMode] = useState<"list" | "create">("list"); // Viewing list or creating?

  // 2. State for creating new secrets
  const [newKey, setNewKey] = useState(""); // The key user is typing
  const [newValue, setNewValue] = useState(""); // The value user is typing
  const [createStep, setCreateStep] = useState<"key" | "value">("key"); // Which field are we on?

  const { exit } = useApp();

  // 3. When component loads, fetch secrets from backend
  useEffect(() => {
    fetchSecrets();
  }, []);

  // 4. Function to get secrets from our backend API
  const fetchSecrets = async () => {
    // 4a. Check if user is logged in
    if (!token) {
      setError("Not authenticated. Please login first.");
      setLoading(false);
      return;
    }

    try {
      // 4b. Call our backend API to get secrets
      const response = await fetch("http://localhost:8001/secrets", {
        headers: {
          Authorization: `Bearer ${token}`, // Send JWT token for auth
        },
      });

      // 4c. Handle the response
      if (response.ok) {
        const data = (await response.json()) as Secret[];
        setSecrets(data); // Save secrets to state
      } else if (response.status === 401) {
        setError("Authentication failed. Please login again.");
      } else {
        setError("Failed to fetch secrets");
      }
    } catch (err) {
      // 4d. Handle network errors
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false); // Stop showing spinner
    }
  };

  // 5. Function to create a new secret
  const createSecret = async () => {
    if (!token) return;

    try {
      // 5a. Send POST request to create secret
      const response = await fetch("http://localhost:8001/secrets", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ key: newKey, value: newValue }),
      });

      // 5b. If successful, reset form and refresh list
      if (response.ok) {
        setNewKey("");
        setNewValue("");
        setMode("list"); // Go back to list view
        setCreateStep("key");
        await fetchSecrets(); // Refresh the list
      } else {
        setError("Failed to create secret");
      }
    } catch (err) {
      setError("Network error");
    }
  };

  // 6. Handle keyboard shortcuts
  useInput((input, key) => {
    if (mode === "list") {
      // 6a. List mode shortcuts
      if (input === "c") {
        // Press 'c' to create new secret
        setMode("create");
        setCreateStep("key");
      } else if (input === "r") {
        // Press 'r' to refresh the list
        setLoading(true);
        fetchSecrets();
      } else if (input === "q") {
        // Press 'q' to go back to main menu
        onBack();
      }
    } else if (mode === "create") {
      // 6b. Create mode shortcuts
      if (key.escape) {
        // Press Escape to cancel
        setMode("list");
        setNewKey("");
        setNewValue("");
        setCreateStep("key");
      } else if (key.return) {
        // Press Enter to continue
        if (createStep === "key" && newKey) {
          setCreateStep("value"); // Move to value input
        } else if (createStep === "value" && newValue) {
          createSecret(); // Submit the secret
        }
      }
    }
  });

  // 7. Show loading spinner while fetching
  if (loading) {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          📝 Secrets
        </Text>
        <Text> </Text>
        <Text>
          <Spinner type="dots" /> Loading secrets...
        </Text>
      </Box>
    );
  }

  // 8. Show error if something went wrong
  if (error) {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          📝 Secrets
        </Text>
        <Text> </Text>
        <Text color="red">Error: {error}</Text>
        <Text> </Text>
        <Text color="gray">Press 'q' to go back</Text>
      </Box>
    );
  }

  // 9. Show create form when user is creating a secret
  if (mode === "create") {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>
          📝 Create New Secret
        </Text>
        <Text> </Text>

        {createStep === "key" ? (
          // 9a. Step 1: Enter the key name
          <Box>
            <Text>Key: </Text>
            <TextInput value={newKey} onChange={setNewKey} />
          </Box>
        ) : (
          // 9b. Step 2: Enter the value
          <>
            <Text color="green">Key: {newKey}</Text>
            <Box>
              <Text>Value: </Text>
              <TextInput value={newValue} onChange={setNewValue} />
            </Box>
          </>
        )}

        <Text> </Text>
        <Text color="gray">Press Enter to continue, Escape to cancel</Text>
      </Box>
    );
  }

  // 10. Show list of secrets (default view)
  return (
    <Box flexDirection="column">
      <Text color="cyan" bold>
        📝 Secrets ({secrets.length})
      </Text>
      <Text> </Text>

      {secrets.length === 0 ? (
        // 10a. Show message if no secrets exist
        <Text color="gray">No secrets yet. Press 'c' to create one.</Text>
      ) : (
        // 10b. Show table of secrets
        <Box flexDirection="column">
          {/* Table header */}
          <Box>
            <Text color="gray" bold>
              {"Key".padEnd(30)} {"Value".padEnd(40)} {"Write"}
            </Text>
          </Box>
          <Text>{"─".repeat(80)}</Text>

          {/* List each secret */}
          {secrets.map((secret) => (
            <Box key={secret.id}>
              <Text color="yellow">
                {secret.key.padEnd(30).substring(0, 30)}{" "}
              </Text>
              <Text>{secret.value.padEnd(40).substring(0, 40)} </Text>
              <Text color={secret.can_write ? "green" : "red"}>
                {secret.can_write ? "✓" : "✗"}
              </Text>
            </Box>
          ))}
        </Box>
      )}

      <Text> </Text>
      <Text color="gray">[c] Create [r] Refresh [q] Back to menu</Text>
    </Box>
  );
};

// Main CLI Component
const App = () => {
  // Part 1F: Track which screen we're on
  const [screen, setScreen] = useState<"menu" | "login" | "secrets" | "logout">(
    "menu"
  );

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
      console.log(
        `Welcome back, ${savedAuth.user.name || savedAuth.user.login}!`
      );
    }
    // Show where config is stored (for debugging)
    console.log(`Config stored at: ${getConfigPath()}`);
  }, []); // Run once on startup

  // 2. Menu options (key added to prevent React warning)
  const menuItems = user
    ? [
        { label: "Logout", value: "logout", key: "logout" },
        { label: "View Secrets", value: "secrets", key: "secrets" },
        { label: "Exit", value: "exit", key: "exit" },
      ]
    : [
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

  // Phase 2E: Secrets Screen Component
  if (screen === "secrets") {
    return <SecretsScreen token={token} onBack={() => setScreen("menu")} />;
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
  console.log("This CLI requires an interactive terminal (TTY).");
  console.log(
    "Please run directly in a terminal, not through pipes or scripts."
  );
  process.exit(1);
}

// 8. Render the app
render(<App />);
