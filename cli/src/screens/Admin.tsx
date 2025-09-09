import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import SelectInput from 'ink-select-input';
import TextInput from 'ink-text-input';
import Spinner from 'ink-spinner';
import { authenticatedFetch } from '../api/client.js';

/**
 * Admin Panel Screen
 * Provides admin operations like creating users/teams, promoting users, etc.
 * Only accessible to users with admin privileges.
 */
export function AdminScreen({ onBack }: { onBack: () => void }) {
  // State for UI modes and data
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'menu' | 'create-user' | 'create-team' | 'manage-users' | 'manage-teams'>('menu');
  const [users, setUsers] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  
  // State for creating new users
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserIsAdmin, setNewUserIsAdmin] = useState(false);
  
  // State for creating new teams
  const [newTeamName, setNewTeamName] = useState('');
  
  // State for multi-step flows
  const [step, setStep] = useState(0);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [selectedTeam, setSelectedTeam] = useState<any>(null);
  
  // Feedback messages
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Load users and teams on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // 1. Fetch users and teams in parallel
      const [usersRes, teamsRes] = await Promise.all([
        authenticatedFetch('/users'),
        authenticatedFetch('/teams')
      ]) as [any, any];
      
      // 2. Update state with fetched data
      setUsers(usersRes.users || []);
      setTeams(teamsRes.teams || []);
    } catch (error) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const createUser = async () => {
    try {
      // 1. Call admin endpoint to create user
      await authenticatedFetch(`/admin/users?email=${encodeURIComponent(newUserEmail)}&name=${encodeURIComponent(newUserName)}&is_admin=${newUserIsAdmin}`, {
        method: 'POST'
      });
      
      // 2. Show success message and return to menu
      setMessage('User created successfully!');
      setMode('menu');
      await loadData();
      
      // 3. Reset form
      setNewUserEmail('');
      setNewUserName('');
      setNewUserIsAdmin(false);
    } catch (error) {
      setError('Failed to create user');
    }
  };

  const createTeam = async () => {
    try {
      // 1. Call endpoint to create team
      await authenticatedFetch('/teams?name=' + encodeURIComponent(newTeamName), {
        method: 'POST'
      });
      
      // 2. Show success and return to menu
      setMessage('Team created successfully!');
      setMode('menu');
      await loadData();
      
      // 3. Reset form
      setNewTeamName('');
    } catch (error) {
      setError('Failed to create team');
    }
  };

  const promoteUser = async (userId: number) => {
    try {
      // 1. Call admin endpoint to promote user
      await authenticatedFetch(`/admin/users/${userId}/promote`, {
        method: 'PUT'
      });
      
      // 2. Show success and reload data
      setMessage('User promoted to admin!');
      await loadData();
    } catch (error) {
      setError('Failed to promote user');
    }
  };

  const deleteUser = async (userId: number) => {
    try {
      // 1. Call admin endpoint to delete user
      await authenticatedFetch(`/admin/users/${userId}`, {
        method: 'DELETE'
      });
      
      // 2. Show success and reload data
      setMessage('User deleted!');
      setSelectedUser(null);
      setMode('manage-users');
      await loadData();
    } catch (error) {
      setError('Failed to delete user');
    }
  };

  const deleteTeam = async (teamId: number) => {
    try {
      // 1. Call admin endpoint to delete team
      await authenticatedFetch(`/admin/teams/${teamId}`, {
        method: 'DELETE'
      });
      
      // 2. Show success and reload data
      setMessage('Team deleted!');
      setSelectedTeam(null);
      setMode('manage-teams');
      await loadData();
    } catch (error) {
      setError('Failed to delete team');
    }
  };

  // Loading state
  if (loading) {
    return (
      <Box flexDirection="column">
        <Text color="cyan"><Spinner type="dots" /> Loading admin panel...</Text>
      </Box>
    );
  }

  // Create user flow - Step 1: Enter email
  if (mode === 'create-user' && step === 0) {
    return (
      <Box flexDirection="column">
        <Text bold color="cyan">🔑 Create New User</Text>
        <Text color="gray">Step 1 of 3</Text>
        <Box marginTop={1}>
          <Text>Enter email address:</Text>
        </Box>
        <TextInput
          value={newUserEmail}
          onChange={setNewUserEmail}
          onSubmit={() => {
            if (newUserEmail) {
              setStep(1);
              setError('');
            } else {
              setError('Email is required');
            }
          }}
        />
        {error && <Text color="red">{error}</Text>}
        <Text color="gray" dimColor>Press Enter to continue, Ctrl+C to cancel</Text>
      </Box>
    );
  }

  // Create user flow - Step 2: Enter name
  if (mode === 'create-user' && step === 1) {
    return (
      <Box flexDirection="column">
        <Text bold color="cyan">🔑 Create New User</Text>
        <Text color="gray">Step 2 of 3</Text>
        <Text>Email: {newUserEmail}</Text>
        <Box marginTop={1}>
          <Text>Enter full name:</Text>
        </Box>
        <TextInput
          value={newUserName}
          onChange={setNewUserName}
          onSubmit={() => {
            if (newUserName) {
              setStep(2);
              setError('');
            } else {
              setError('Name is required');
            }
          }}
        />
        {error && <Text color="red">{error}</Text>}
      </Box>
    );
  }

  // Create user flow - Step 3: Admin privileges
  if (mode === 'create-user' && step === 2) {
    const items = [
      { label: 'Regular User', value: 'regular' },
      { label: 'Admin User', value: 'admin' }
    ];

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">🔑 Create New User</Text>
        <Text color="gray">Step 3 of 3</Text>
        <Text>Email: {newUserEmail}</Text>
        <Text>Name: {newUserName}</Text>
        <Box marginTop={1}>
          <Text>Select user role:</Text>
        </Box>
        <SelectInput
          items={items}
          onSelect={(item) => {
            setNewUserIsAdmin(item.value === 'admin');
            createUser();
          }}
        />
      </Box>
    );
  }

  // Create team flow
  if (mode === 'create-team') {
    return (
      <Box flexDirection="column">
        <Text bold color="cyan">👥 Create New Team</Text>
        <Box marginTop={1}>
          <Text>Enter team name:</Text>
        </Box>
        <TextInput
          value={newTeamName}
          onChange={setNewTeamName}
          onSubmit={() => {
            if (newTeamName) {
              createTeam();
            } else {
              setError('Team name is required');
            }
          }}
        />
        {error && <Text color="red">{error}</Text>}
        <Text color="gray" dimColor>Press Enter to create, Ctrl+C to cancel</Text>
      </Box>
    );
  }

  // Manage users - List
  if (mode === 'manage-users' && !selectedUser) {
    const items: any[] = users.map(user => ({
      label: `${user.name} (${user.email}) ${user.is_admin ? '🔑' : ''}`,
      value: `user-${user.id}`,
      user
    }));
    items.push({ label: '← Back to Admin Menu', value: 'back', user: null });

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">⚙️ Manage Users</Text>
        <Text color="gray">Select a user to manage ({users.length} users)</Text>
        {message && <Text color="green">✓ {message}</Text>}
        {error && <Text color="red">✗ {error}</Text>}
        <Box marginTop={1}>
          <SelectInput
            items={items}
            onSelect={(item: any) => {
              setMessage('');
              setError('');
              if (item.value === 'back') {
                setMode('menu');
              } else if (item.user) {
                setSelectedUser(item.user);
              }
            }}
          />
        </Box>
      </Box>
    );
  }

  // Manage users - Actions for selected user
  if (mode === 'manage-users' && selectedUser) {
    const actions = [];
    
    // Only show promote if user is not already admin
    if (!selectedUser.is_admin) {
      actions.push({ label: '🔑 Promote to Admin', value: 'promote' });
    }
    
    actions.push(
      { label: '🗑️ Delete User', value: 'delete' },
      { label: '← Back to User List', value: 'back' }
    );

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">User Actions</Text>
        <Text>User: {selectedUser.name}</Text>
        <Text>Email: {selectedUser.email}</Text>
        <Text>Role: {selectedUser.is_admin ? '🔑 Admin' : '👤 Regular User'}</Text>
        {message && <Text color="green">✓ {message}</Text>}
        {error && <Text color="red">✗ {error}</Text>}
        <Box marginTop={1}>
          <SelectInput
            items={actions}
            onSelect={(item) => {
              setMessage('');
              setError('');
              if (item.value === 'back') {
                setSelectedUser(null);
              } else if (item.value === 'promote') {
                promoteUser(selectedUser.id);
                setSelectedUser(null);
              } else if (item.value === 'delete') {
                // Confirm deletion
                deleteUser(selectedUser.id);
              }
            }}
          />
        </Box>
      </Box>
    );
  }

  // Manage teams - List
  if (mode === 'manage-teams' && !selectedTeam) {
    const items: any[] = teams.map(team => ({
      label: team.name,
      value: `team-${team.id}`,
      team
    }));
    items.push({ label: '← Back to Admin Menu', value: 'back', team: null });

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">⚙️ Manage Teams</Text>
        <Text color="gray">Select a team to manage ({teams.length} teams)</Text>
        {message && <Text color="green">✓ {message}</Text>}
        {error && <Text color="red">✗ {error}</Text>}
        <Box marginTop={1}>
          <SelectInput
            items={items}
            onSelect={(item: any) => {
              setMessage('');
              setError('');
              if (item.value === 'back') {
                setMode('menu');
              } else if (item.team) {
                setSelectedTeam(item.team);
              }
            }}
          />
        </Box>
      </Box>
    );
  }

  // Manage teams - Actions for selected team
  if (mode === 'manage-teams' && selectedTeam) {
    const actions = [
      { label: '🗑️ Delete Team', value: 'delete' },
      { label: '← Back to Team List', value: 'back' }
    ];

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">Team Actions</Text>
        <Text>Team: {selectedTeam.name}</Text>
        {message && <Text color="green">✓ {message}</Text>}
        {error && <Text color="red">✗ {error}</Text>}
        <Box marginTop={1}>
          <SelectInput
            items={actions}
            onSelect={(item) => {
              setMessage('');
              setError('');
              if (item.value === 'back') {
                setSelectedTeam(null);
              } else if (item.value === 'delete') {
                deleteTeam(selectedTeam.id);
              }
            }}
          />
        </Box>
      </Box>
    );
  }

  // Main admin menu
  const menuItems = [
    { label: '👤 Create User', value: 'create-user' },
    { label: '👥 Create Team', value: 'create-team' },
    { label: '⚙️ Manage Users', value: 'manage-users' },
    { label: '⚙️ Manage Teams', value: 'manage-teams' },
    { label: '← Back to Main Menu', value: 'back' }
  ];

  return (
    <Box flexDirection="column">
      <Text bold color="cyan">🔑 Admin Panel</Text>
      <Text color="gray">Administrative operations</Text>
      {message && <Text color="green">✓ {message}</Text>}
      {error && <Text color="red">✗ {error}</Text>}
      <Box marginTop={1}>
        <SelectInput
          items={menuItems}
          onSelect={(item) => {
            // Clear messages when navigating
            setMessage('');
            setError('');
            
            if (item.value === 'back') {
              onBack();
            } else if (item.value === 'create-user') {
              setMode('create-user');
              setStep(0);
              setNewUserEmail('');
              setNewUserName('');
              setNewUserIsAdmin(false);
            } else if (item.value === 'create-team') {
              setMode('create-team');
              setNewTeamName('');
            } else if (item.value === 'manage-users') {
              setMode('manage-users');
              setSelectedUser(null);
            } else if (item.value === 'manage-teams') {
              setMode('manage-teams');
              setSelectedTeam(null);
            }
          }}
        />
      </Box>
    </Box>
  );
}