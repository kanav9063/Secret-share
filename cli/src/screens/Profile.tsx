import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import SelectInput from 'ink-select-input';
import Spinner from 'ink-spinner';
import { authenticatedFetch } from '../api/client.js';

/**
 * Profile Screen - Phase 4
 * Shows current user's profile information including:
 * - Name and email
 * - Organization
 * - Admin status
 * - Team memberships
 */
export function ProfileScreen({ onBack }: { onBack: () => void }) {
  // State for user profile data
  const [userInfo, setUserInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load user profile on mount
  useEffect(() => {
    loadUserInfo();
  }, []);

  const loadUserInfo = async () => {
    try {
      // 1. Call the /me endpoint to get user info
      const data = await authenticatedFetch('/me');
      
      // 2. Update state with user data
      setUserInfo(data);
    } catch (error) {
      // 3. Handle errors
      setError('Failed to load profile information');
      console.error('Profile load error:', error);
    } finally {
      setLoading(false);
    }
  };

  // Show loading spinner
  if (loading) {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>USER PROFILE</Text>
        <Text> </Text>
        <Text color="cyan"><Spinner type="dots" /> Loading profile...</Text>
      </Box>
    );
  }

  // Show error state
  if (error || !userInfo) {
    return (
      <Box flexDirection="column">
        <Text color="cyan" bold>USER PROFILE</Text>
        <Text> </Text>
        <Text color="red">[ERROR] {error || 'Failed to load profile'}</Text>
        <Text> </Text>
        <SelectInput
          items={[{ label: 'Back to Main Menu', value: 'back' }]}
          onSelect={() => onBack()}
        />
      </Box>
    );
  }

  // Menu items for navigation
  const items = [{ label: 'Back to Main Menu', value: 'back' }];

  // Main profile display
  return (
    <Box flexDirection="column">
      <Box borderStyle="single" borderColor="cyan" paddingX={1}>
        <Text color="cyan" bold>USER PROFILE</Text>
      </Box>
      <Text> </Text>
      
      {/* User Information Section */}
      <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1}>
        <Text bold>USER INFORMATION</Text>
        <Text>───────────────────────────────────────</Text>
        <Box>
          <Text color="gray">Name: </Text>
          <Text>{userInfo.user.name}</Text>
        </Box>
        <Box>
          <Text color="gray">Email: </Text>
          <Text>{userInfo.user.email}</Text>
        </Box>
        <Box>
          <Text color="gray">Role: </Text>
          <Text color={userInfo.user.is_admin ? "green" : "cyan"}>
            {userInfo.user.is_admin ? 'Administrator' : 'Regular User'}
          </Text>
        </Box>
        <Box>
          <Text color="gray">Status: </Text>
          <Text color="green">✓ Active</Text>
        </Box>
      </Box>
      
      <Text> </Text>
      
      {/* Organization Section */}
      <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1}>
        <Text bold>ORGANIZATION</Text>
        <Text>───────────────────────────────────────</Text>
        <Box>
          <Text color="gray">Name: </Text>
          <Text>{userInfo.organization?.name || 'No organization'}</Text>
        </Box>
        {userInfo.organization && (
          <Box>
            <Text color="gray">ID: </Text>
            <Text>#{userInfo.organization.id}</Text>
          </Box>
        )}
      </Box>
      
      <Text> </Text>
      
      {/* Teams Section */}
      <Box flexDirection="column" borderStyle="single" borderColor="gray" paddingX={1}>
        <Text bold>TEAM MEMBERSHIPS ({userInfo.teams.length})</Text>
        <Text>───────────────────────────────────────</Text>
        {userInfo.teams.length === 0 ? (
          <Text color="gray">Not a member of any teams</Text>
        ) : (
          userInfo.teams.map((team: any) => (
            <Box key={team.id}>
              <Text color="green">• </Text>
              <Text>{team.name}</Text>
              <Text color="gray"> (#{team.id})</Text>
            </Box>
          ))
        )}
      </Box>
      
      <Text> </Text>
      
      {/* Admin Actions (if admin) */}
      {userInfo.user.is_admin && (
        <>
          <Box borderStyle="single" borderColor="green" paddingX={1}>
            <Text color="green" bold>⚡ ADMIN Privileges Active</Text>
            <Text color="gray">Full access to administrative operations</Text>
          </Box>
          <Text> </Text>
        </>
      )}
      
      {/* Navigation */}
      <SelectInput items={items} onSelect={() => onBack()} />
    </Box>
  );
}