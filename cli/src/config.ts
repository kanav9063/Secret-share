// Phase 1H: Token Persistence
// This file handles saving and loading user authentication data to/from disk
// so users don't have to login every time they run the CLI

import Conf from "conf";

// 1. Create a persistent configuration store using the 'conf' library
// This automatically creates a config file at ~/.config/secret-cli/config.json
// The schema defines what data we can store and validates it for us
const config = new Conf({
  projectName: "secret-cli", // This becomes the folder name in ~/.config/
  schema: {
    // Define the structure of data we want to store
    token: {
      type: "string", // JWT token must be a string
    },
    user: {
      type: "object", // User info is an object with these properties:
      properties: {
        id: { type: "number" }, // GitHub user ID (required)
        login: { type: "string" }, // GitHub username (required)
        name: { type: ["string", "null"] }, // Display name (optional)
        email: { type: ["string", "null"] }, // Email address (optional)
      },
    },
  },
});

// 2. Save authentication data to disk for future CLI sessions
// This is called after successful OAuth login to remember the user
export function saveAuth(token: string, user: any): void {
  // Use conf library to save data - it handles file writing automatically
  config.set("token", token); // Save the JWT token for API calls
  config.set("user", user); // Save user profile info for display
  console.log("✅ Session saved to disk");
}

// 3. Load saved authentication data from disk when CLI starts
// This is called on every CLI startup to restore the user's session
export function loadAuth(): { token: string | null; user: any | null } {
  // Try to get saved data from the config file
  const token = config.get("token") as string | undefined;
  const user = config.get("user") as any | undefined;

  // Only proceed if we have both token and user data
  if (token && user) {
    // 4. Check if the JWT token is expired before using it
    // This prevents using old, invalid tokens that would cause API errors
    const tokenPayload = parseJWT(token); // Decode the JWT to check expiration

    if (tokenPayload && tokenPayload.exp) {
      // Convert Unix timestamp to JavaScript Date object
      const expiry = new Date(tokenPayload.exp * 1000);

      // Check if token is still valid (not expired)
      if (expiry > new Date()) {
        // Token is still good, return the saved data
        return { token, user };
      } else {
        // Token has expired, clean it up and ask user to login again
        clearAuth(); // Remove expired data from disk
        console.log("⚠️  Saved token expired, please login again");
      }
    }
  }

  // Return null values if no valid auth data was found
  return { token: null, user: null };
}

// 5. Clear all saved authentication data from disk
// This is called when user logs out to ensure clean session termination
export function clearAuth(): void {
  // Remove both token and user data from the config file
  config.delete("token"); // Delete the JWT token
  config.delete("user"); // Delete the user profile
}

// 6. Get the file system path where configuration is stored
// This is useful for debugging and showing users where their data is saved
export function getConfigPath(): string {
  // Return the full path to the config file (e.g., ~/.config/secret-cli/config.json)
  return config.path;
}

// 7. Helper function to decode JWT tokens and extract expiration time
// This is a basic implementation that doesn't verify the signature (for production use)
function parseJWT(token: string): any {
  try {
    // JWT tokens have 3 parts separated by dots: header.payload.signature
    const parts = token.split(".");

    // Validate that we have all 3 parts
    if (parts.length !== 3) return null;

    // Get the payload (middle part) which contains the data we need
    const payload = parts[1];

    // Decode the base64-encoded payload to get the JSON data
    const decoded = Buffer.from(payload, "base64").toString("utf-8");

    // Parse the JSON to get the actual data object
    return JSON.parse(decoded);
  } catch {
    // If anything goes wrong (invalid token format, etc.), return null
    return null;
  }
}
