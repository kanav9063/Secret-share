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
import { TeamsScreen } from "./screens/Teams.js"; // Phase 3D: Teams management screen
import { AdminScreen } from "./screens/Admin.js"; // Phase 4: Admin panel
import { ProfileScreen } from "./screens/Profile.js"; // Phase 4: User profile

// Phase 3E: Enhanced TypeScript interface for our secret data
interface Secret {
  id: number;
  key: string;
  value: string;
  created_by: number;  // Changed from created_by_id
  created_by_name: string;  // New: creator's name
  created_at: string;
  can_write: boolean;
  is_creator: boolean;  // New: am I the creator?
  shared_with: {  // New: detailed sharing info
    users: Array<{
      id: number;
      name: string;
      email: string;
      can_write: boolean;
    }>;
    teams: Array<{
      id: number;
      name: string;
      can_write: boolean;
    }>;
    org_wide: boolean;
    org_can_write?: boolean;
  };
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
  const [mode, setMode] = useState<"list" | "create" | "delete">("list"); // Phase 4: Added delete mode

  // 2. State for creating new secrets with simple sharing
  const [newKey, setNewKey] = useState(""); // The key user is typing
  const [newValue, setNewValue] = useState(""); // The value user is typing
  const [createStep, setCreateStep] = useState<"key" | "value" | "sharing" | "permissions">("key");
  const [sharingChoice, setSharingChoice] = useState<"private" | "team" | "org">("private");
  const [grantWrite, setGrantWrite] = useState(false); // Read-only (false) or read-write (true)?
  
  // Phase 4: State for deleting secrets
  const [selectedIndex, setSelectedIndex] = useState(0); // Which secret is selected
  const [deleteTarget, setDeleteTarget] = useState<Secret | null>(null); // Secret to delete
  
  // State for user's teams (for auto-sharing)
  const [userTeams, setUserTeams] = useState<any[]>([]);

  const { exit } = useApp();

  // 3. When component loads, fetch secrets and user's teams from backend
  useEffect(() => {
    fetchSecrets();
    fetchUserTeams();
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
        setError("[ERROR] Unable to retrieve secrets");
      }
    } catch (err) {
      // 4d. Handle network errors
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false); // Stop showing spinner
    }
  };

  // Function to fetch user's teams for auto-sharing
  const fetchUserTeams = async () => {
    if (!token) return;
    
    try {
      const response = await fetch("http://localhost:8001/teams/mine", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json() as { teams: any[] };
        setUserTeams(data.teams || []);
      }
    } catch (err) {
      // Silently fail - teams are optional for sharing
    }
  };

  // 5. Function to create a new secret with simple sharing
  const createSecret = async () => {
    if (!token) return;

    // Build ACL entries based on sharing selection
    const acl_entries = [];
    
    if (sharingChoice === "team") {
      // Share with all user's teams automatically
      for (const team of userTeams) {
        acl_entries.push({
          subject_type: "team",
          subject_id: team.id,
          can_read: true,
          can_write: grantWrite
        });
      }
    } else if (sharingChoice === "org") {
      // Share with entire organization
      acl_entries.push({
        subject_type: "org",
        subject_id: null,
        can_read: true,
        can_write: grantWrite
      });
    }
    // If "private", acl_entries stays empty (only creator has access)

    try {
      // 5a. Send POST request to create secret with ACL
      const response = await fetch("http://localhost:8001/secrets", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          key: newKey, 
          value: newValue,
          acl_entries: acl_entries
        }),
      });

      // 5b. If successful, reset form and refresh list
      if (response.ok) {
        setNewKey("");
        setNewValue("");
        setSharingChoice("private");
        setGrantWrite(false);
        setMode("list"); // Go back to list view
        setCreateStep("key");
        await fetchSecrets(); // Refresh the list
      } else {
        setError("[ERROR] Unable to create secret");
      }
    } catch (err) {
      setError("Network error");
    }
  };

  // Phase 4: Function to delete a secret
  const deleteSecret = async (secret: Secret) => {
    if (!token) return;

    try {
      // 1. Send DELETE request to backend
      const response = await fetch(`http://localhost:8001/secrets/${secret.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // 2. Handle response
      if (response.ok) {
        setMode("list"); // Go back to list
        setDeleteTarget(null);
        await fetchSecrets(); // Refresh the list
      } else if (response.status === 403) {
        setError("You can only delete secrets you created");
      } else {
        setError("[ERROR] Unable to delete secret");
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
      } else if (input === "d" && secrets.length > 0) {
        // Phase 4: Press 'd' to delete selected secret
        const secret = secrets[selectedIndex];
        if (secret && secret.is_creator) {
          setDeleteTarget(secret);
          setMode("delete");
        } else {
          setError("You can only delete secrets you created");
          setTimeout(() => setError(null), 3000);
        }
      } else if (input === "r") {
        // Press 'r' to refresh the list
        setLoading(true);
        fetchSecrets();
      } else if (input === "q") {
        // Press 'q' to go back to main menu
        onBack();
      } else if (key.upArrow && selectedIndex > 0) {
        // Navigate up in the list
        setSelectedIndex(selectedIndex - 1);
      } else if (key.downArrow && selectedIndex < secrets.length - 1) {
        // Navigate down in the list
        setSelectedIndex(selectedIndex + 1);
      }
    } else if (mode === "create") {
      // 6b. Create mode shortcuts
      if (key.escape) {
        // Press Escape to cancel
        setMode("list");
        setNewKey("");
        setNewValue("");
        setCreateStep("key");
        setSharingChoice("private");
        setGrantWrite(false);
      } else if (key.return) {
        // Press Enter to continue
        if (createStep === "key" && newKey) {
          setCreateStep("value"); // Move to value input
        } else if (createStep === "value" && newValue) {
          setCreateStep("sharing"); // Move to sharing options
        }
        // Sharing and permissions steps are handled by SelectInput onSelect
      }
    } else if (mode === "delete") {
      // Phase 4: Delete mode shortcuts
      if (input === "y" && deleteTarget) {
        // Confirm delete
        deleteSecret(deleteTarget);
      } else if (input === "n" || key.escape) {
        // Cancel delete
        setMode("list");
        setDeleteTarget(null);
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
        <Text color="cyan">
          <Spinner type="dots" /> Loading...
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
        <Text color="red">[ERROR] {error}</Text>
        <Text> </Text>
        <Text color="gray">Press 'q' to go back</Text>
      </Box>
    );
  }

  // 9. Show create form when user is creating a secret
  if (mode === "create") {
    // Step 1: Enter key
    if (createStep === "key") {
      return (
        <Box flexDirection="column">
          <Text color="cyan" bold>📝 Create New Secret - Step 1/4</Text>
          <Text> </Text>
          <Box>
            <Text>Key: </Text>
            <TextInput value={newKey} onChange={setNewKey} />
          </Box>
          <Text> </Text>
          <Text color="gray">Press Enter to continue, Escape to cancel</Text>
        </Box>
      );
    }
    
    // Step 2: Enter value
    if (createStep === "value") {
      return (
        <Box flexDirection="column">
          <Text color="cyan" bold>📝 Create New Secret - Step 2/4</Text>
          <Text> </Text>
          <Text color="green">Key: {newKey}</Text>
          <Box>
            <Text>Value: </Text>
            <TextInput value={newValue} onChange={setNewValue} />
          </Box>
          <Text> </Text>
          <Text color="gray">Press Enter to continue, Escape to cancel</Text>
        </Box>
      );
    }
    
    // Step 3: Choose sharing
    if (createStep === "sharing") {
      const sharingItems = [
        { label: "🔒 Private (only you)", value: "private" },
        { label: "👥 My Team" + (userTeams.length > 0 ? ` (${userTeams.map(t => t.name).join(", ")})` : ""), value: "team" },
        { label: "🌐 Entire Organization", value: "org" }
      ];
      
      return (
        <Box flexDirection="column">
          <Text color="cyan" bold>📝 Create New Secret - Step 3/4</Text>
          <Text> </Text>
          <Text color="green">Key: {newKey}</Text>
          <Text>Value: {newValue.substring(0, 20) + (newValue.length > 20 ? "..." : "")}</Text>
          <Text> </Text>
          <Text bold>Who can access this secret?</Text>
          <Text> </Text>
          <SelectInput
            items={sharingItems}
            onSelect={(item) => {
              setSharingChoice(item.value as "private" | "team" | "org");
              if (item.value === "private") {
                // Skip permissions step for private secrets
                createSecret();
              } else {
                setCreateStep("permissions");
              }
            }}
          />
        </Box>
      );
    }
    
    // Step 4: Choose permissions (only if sharing)
    if (createStep === "permissions") {
      const permissionItems = [
        { label: "👁  Read-only", value: "read" },
        { label: "✏️  Read & Write", value: "write" }
      ];
      
      return (
        <Box flexDirection="column">
          <Text color="cyan" bold>📝 Create New Secret - Step 4/4</Text>
          <Text> </Text>
          <Text color="green">Key: {newKey}</Text>
          <Text>Value: {newValue.substring(0, 20) + (newValue.length > 20 ? "..." : "")}</Text>
          <Text>Sharing: {sharingChoice === "team" ? "My Team" : "Organization"}</Text>
          <Text> </Text>
          <Text bold>What permission level?</Text>
          <Text> </Text>
          <SelectInput
            items={permissionItems}
            onSelect={(item) => {
              setGrantWrite(item.value === "write");
              createSecret();
            }}
          />
        </Box>
      );
    }
  }

  // Phase 4: Show delete confirmation
  if (mode === "delete" && deleteTarget) {
    return (
      <Box flexDirection="column">
        <Text color="red" bold>
          ⚠️ Delete Secret
        </Text>
        <Text> </Text>
        <Text>Are you sure you want to delete this secret?</Text>
        <Text> </Text>
        <Text color="yellow">Key: {deleteTarget.key}</Text>
        <Text>Value: {deleteTarget.value}</Text>
        <Text> </Text>
        <Text color="red" bold>This action cannot be undone!</Text>
        <Text> </Text>
        <Text>Press 'y' to confirm, 'n' or Escape to cancel</Text>
      </Box>
    );
  }

  // 10. Show list of secrets (default view) - Phase 3E Enhanced
  return (
    <Box flexDirection="column">
      <Text color="cyan" bold>
        📝 Secrets ({secrets.length})
      </Text>
      <Text> </Text>

      {secrets.length === 0 ? (
        // 10a. Show message if no secrets exist
        <Text color="gray">No secrets found. Press 'c' to create.</Text>
      ) : (
        // 10b. Show enhanced table of secrets with sharing info
        <Box flexDirection="column">
          {/* Table header - Phase 3E: Added Sharing column */}
          <Box>
            <Text color="gray" bold>
              {"Key".padEnd(25)} {"Value".padEnd(30)} {"Creator".padEnd(15)} {"Sharing".padEnd(10)} {"Access"}
            </Text>
          </Box>
          <Text>{"─".repeat(95)}</Text>

          {/* List each secret with enhanced info */}
          {secrets.map((secret, index) => {
            // Build sharing indicators (Phase 3E)
            let sharingIcons = "";
            if (secret.shared_with.org_wide) {
              sharingIcons += "🌐 ";  // Organization-wide
            }
            if (secret.shared_with.teams.length > 0) {
              sharingIcons += "👥 ";  // Shared with teams
            }
            if (secret.shared_with.users.length > 0) {
              sharingIcons += "👤 ";  // Shared with specific users
            }
            if (!sharingIcons) {
              sharingIcons = "🔒 ";  // Private (only creator)
            }

            // Determine access level
            let accessText = "";
            let accessColor = "yellow";
            if (secret.is_creator) {
              accessText = "Owner";
              accessColor = "green";
            } else if (secret.can_write) {
              accessText = "Write";
              accessColor = "cyan";
            } else {
              accessText = "Read";
              accessColor = "gray";
            }

            // Phase 4: Highlight selected row
            const isSelected = index === selectedIndex;

            return (
              <Box key={secret.id}>
                <Text color={isSelected ? "blue" : undefined} bold={isSelected}>
                  {isSelected ? "▶ " : "  "}
                </Text>
                <Text color="yellow">
                  {secret.key.padEnd(25).substring(0, 25)}{" "}
                </Text>
                <Text>
                  {secret.value.padEnd(30).substring(0, 30)}{" "}
                </Text>
                <Text color="magenta">
                  {secret.created_by_name.padEnd(15).substring(0, 15)}{" "}
                </Text>
                <Text>
                  {sharingIcons.padEnd(10)}{" "}
                </Text>
                <Text color={accessColor}>
                  {accessText}
                </Text>
              </Box>
            );
          })}

          {/* Legend for sharing icons */}
          <Text> </Text>
          <Text color="gray">
            🔒=Private  👤=Users  👥=Teams  🌐=Organization
          </Text>
        </Box>
      )}

      <Text> </Text>
      {error && <Text color="red">⚠️ {error}</Text>}
      <Text color="gray">[↑↓] Navigate [c] Create [d] Delete (owners only) [r] Refresh [q] Back</Text>
    </Box>
  );
};

// Main CLI Component
const App = () => {
  // Part 1F: Track which screen we're on - Phase 4: Added admin and profile
  const [screen, setScreen] = useState<"menu" | "login" | "secrets" | "teams" | "admin" | "profile" | "logout">(
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

  // 2. Menu options - Phase 4: Added profile and admin options
  const menuItems = user
    ? [
        { label: "👤 Profile", value: "profile", key: "profile" },  // Phase 4: Profile
        { label: "🔐 Secrets Management", value: "secrets", key: "secrets" },
        { label: "👥 Teams", value: "teams", key: "teams" },  // Phase 3D: Teams option
        ...(user.is_admin ? [{ label: "⚡ Admin Panel", value: "admin", key: "admin" }] : []),  // Phase 4: Admin only
        { label: "──────────────", value: "divider", key: "divider" },
        { label: "↩ Logout", value: "logout", key: "logout" },
        { label: "✕ Exit", value: "exit", key: "exit" },
      ]
    : [
        { label: "Login with GitHub", value: "login", key: "login" },
        { label: "View Secrets (Read-only)", value: "secrets", key: "secrets" },
        { label: "Exit", value: "exit", key: "exit" },
      ];

  // 3. Handle menu selection
  const handleSelect = (item: any) => {
    if (item.value === "divider") {
      return; // Ignore divider selection
    } else if (item.value === "exit") {
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
    } else if (item.value === "teams") {
      setScreen("teams");  // Phase 3D: Handle teams selection
    } else if (item.value === "admin") {
      setScreen("admin");  // Phase 4: Handle admin panel
    } else if (item.value === "profile") {
      setScreen("profile");  // Phase 4: Handle profile
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
      console.error("[ERROR] OAuth initialization failed:", error);
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
        <Box borderStyle="double" borderColor="cyan" paddingX={1}>
          <Text color="cyan" bold>
            SECRET SHARING SYSTEM v1.0
          </Text>
        </Box>
        <Text> </Text>
        {user && (
          <Text color="gray">
            Authenticated as: {user.name || user.login}
          </Text>
        )}
        <Text> </Text>
        <Text>Select an option:</Text>
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

  // Phase 3D: Teams Screen Component
  if (screen === "teams") {
    return <TeamsScreen onBack={() => setScreen("menu")} />;
  }

  // Phase 4: Admin Panel Screen
  if (screen === "admin") {
    return <AdminScreen onBack={() => setScreen("menu")} />;
  }

  // Phase 4: Profile Screen
  if (screen === "profile") {
    return <ProfileScreen onBack={() => setScreen("menu")} />;
  }

  if (screen === "logout") {
    return (
      <Box flexDirection="column">
        <Text color="yellow">Terminating session...</Text>
        <Text color="gray">Returning to menu</Text>
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
