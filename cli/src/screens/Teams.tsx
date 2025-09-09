import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import SelectInput from 'ink-select-input';
import Spinner from 'ink-spinner';
import { authenticatedFetch } from '../api/client.js';

// TypeScript interfaces for our data
interface Team {
  id: number;
  name: string;
  organization_id: number;
  created_at: string;
}

interface TeamMember {
  id: number;
  name: string;
  email: string;
  github_id: string;
  is_admin: boolean;
}

export function TeamsScreen({ onBack }: { onBack: () => void }) {
  // State management
  const [teams, setTeams] = useState<Team[]>([]);  // All teams in org
  const [myTeams, setMyTeams] = useState<Team[]>([]);  // Teams I'm in
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'list' | 'detail'>('list');  // Which view to show
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);

  // Load teams when component mounts
  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      // 1. Fetch both all teams and my teams in parallel
      const [allTeamsRes, myTeamsRes] = await Promise.all([
        authenticatedFetch('/teams'),       // All teams in org
        authenticatedFetch('/teams/mine')    // Teams I'm a member of
      ]) as [any, any];  // Type assertion for API responses
      
      // 2. Update state with the data
      setTeams(allTeamsRes.teams || []);
      setMyTeams(myTeamsRes.teams || []);
    } catch (error) {
      console.error('Failed to load teams:', error);
      // Set empty arrays on error
      setTeams([]);
      setMyTeams([]);
    } finally {
      setLoading(false);
    }
  };

  const loadTeamMembers = async (teamId: number) => {
    setLoading(true);
    try {
      // 1. Fetch members for specific team
      const res = await authenticatedFetch(`/teams/${teamId}/members`) as any;
      
      // 2. Update state with members
      setMembers(res.members || []);
      setView('detail');  // Switch to detail view
    } catch (error) {
      console.error('Failed to load team members:', error);
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  // Show loading spinner
  if (loading) {
    return (
      <Box flexDirection="column">
        <Text color="cyan">
          <Spinner type="dots" /> Loading teams...
        </Text>
      </Box>
    );
  }

  // Detail view - showing members of a specific team
  if (view === 'detail' && selectedTeam) {
    // 1. Build menu items for each member
    const items = members.map(member => ({
      label: `${member.name} (${member.email})${member.is_admin ? ' - Admin' : ''}`,
      value: `member-${member.id}`
    }));
    
    // 2. Add back option
    items.push({ label: '← Back to teams', value: 'back' });

    return (
      <Box flexDirection="column">
        <Text bold color="cyan">Team: {selectedTeam.name}</Text>
        <Text color="gray">Members ({members.length}):</Text>
        <Box marginTop={1}>
          <SelectInput
            items={items}
            onSelect={(item) => {
              if (item.value === 'back') {
                setView('list');
                setSelectedTeam(null);
                setMembers([]);
              }
              // Could add member actions here in future
            }}
          />
        </Box>
      </Box>
    );
  }

  // List view - showing all teams
  // 1. Build menu items for each team
  const items: any[] = teams.map(team => {
    // Check if I'm a member of this team
    const isMember = myTeams.some(t => t.id === team.id);
    
    return {
      label: `${team.name} ${isMember ? '✓' : ''}`,  // Add checkmark if member
      value: `team-${team.id}`,
      team  // Store team object for later use
    };
  });
  
  // 2. Add back to menu option
  items.push({ 
    label: '← Back to main menu', 
    value: 'back',
    team: null 
  });

  return (
    <Box flexDirection="column">
      <Text bold color="cyan">Teams in Organization</Text>
      <Text color="gray">✓ = You are a member</Text>
      <Box marginTop={1}>
        <SelectInput
          items={items}
          onSelect={(item: any) => {
            if (item.value === 'back') {
              // Go back to main menu
              onBack();
            } else if (item.team) {
              // User selected a team - load its members
              setSelectedTeam(item.team);
              loadTeamMembers(item.team.id);
            }
          }}
        />
      </Box>
    </Box>
  );
}