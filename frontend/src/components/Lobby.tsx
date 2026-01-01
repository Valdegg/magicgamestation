import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCardDatabase } from '../context/CardDatabaseContext';
import { getUniqueCardNames, getCardImagePaths } from '../utils/cardDatabase';
import { API_BASE } from '../api/gameApi';
import { LobbyChat } from './LobbyChat';

interface GameMetadata {
  game_id: string;
  name: string;
  player_count: number;
  player_names: string[];
}

interface LobbyProps {
  onJoinGame: (gameId: string, playerId: string) => void;
}

const Lobby: React.FC<LobbyProps> = ({ onJoinGame }) => {
  const { database, reload } = useCardDatabase();
  const [games, setGames] = useState<GameMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showDeckModal, setShowDeckModal] = useState(false);
  const [gameName, setGameName] = useState('');
  const [userName, setUserName] = useState('');
  const [deckText, setDeckText] = useState('');
  const [deckName, setDeckName] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // Card Search State
  const [cardSearchTerm, setCardSearchTerm] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [scryfallSuggestions, setScryfallSuggestions] = useState<string[]>([]);
  const [isLoadingScryfallSuggestions, setIsLoadingScryfallSuggestions] = useState(false);
  
  // Track cards being fetched to avoid duplicate requests
  const [fetchingCards, setFetchingCards] = useState<Set<string>>(new Set());
  const [fetchedCards, setFetchedCards] = useState<Set<string>>(new Set());

  const allCardNames = useMemo(() => getUniqueCardNames(database), [database]);
  
  // Parse count and card name from search term (e.g., "4 Lightning Bolt" or "Lightning Bolt")
  const { count: searchCount, cardName: searchCardName } = useMemo(() => {
    const trimmed = cardSearchTerm.trim();
    const match = trimmed.match(/^(\d+)\s+(.+)$/);
    if (match) {
      return { count: parseInt(match[1]), cardName: match[2] };
    }
    return { count: 1, cardName: trimmed }; // Default to 1 if no number specified
  }, [cardSearchTerm]);
  
  // Local database filtered cards
  const localFilteredCards = useMemo(() => {
    if (!searchCardName.trim()) return [];
    const term = searchCardName.toLowerCase();
    return allCardNames
      .filter(name => name.toLowerCase().startsWith(term))
      .slice(0, 10);
  }, [allCardNames, searchCardName]);

  // Fetch Scryfall autocomplete suggestions
  const fetchScryfallAutocomplete = async (searchTerm: string) => {
    if (!searchTerm || searchTerm.length < 2) {
      setScryfallSuggestions([]);
      return;
    }

    setIsLoadingScryfallSuggestions(true);
    try {
      const response = await fetch(
        `https://api.scryfall.com/cards/autocomplete?q=${encodeURIComponent(searchTerm)}`
      );
      
      if (response.ok) {
        const data = await response.json();
        // Filter out cards we already have locally
        const localCardNamesLower = allCardNames.map(n => n.toLowerCase());
        const uniqueSuggestions = data.data.filter(
          (name: string) => !localCardNamesLower.includes(name.toLowerCase())
        );
        setScryfallSuggestions(uniqueSuggestions.slice(0, 5)); // Max 5 Scryfall suggestions
      }
    } catch (error) {
      console.error('Failed to fetch Scryfall autocomplete:', error);
      setScryfallSuggestions([]);
    } finally {
      setIsLoadingScryfallSuggestions(false);
    }
  };

  // Debounced Scryfall autocomplete
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchCardName && localFilteredCards.length < 5) {
        // Only fetch from Scryfall if we have fewer than 5 local matches
        fetchScryfallAutocomplete(searchCardName);
      } else {
        setScryfallSuggestions([]);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [searchCardName, localFilteredCards.length]);

  // Combine local and Scryfall suggestions
  const filteredCards = useMemo(() => {
    return [...localFilteredCards, ...scryfallSuggestions];
  }, [localFilteredCards, scryfallSuggestions]);

  // Parse deck text to extract card names for visual preview
  // Split main deck and sideboard when encountering "SIDEBOARD:"
  const { deckCards, sideboardCards } = useMemo(() => {
    const mainCards: string[] = [];
    const sideboardCards: string[] = [];
    let isSideboard = false;
    
    const lines = deckText.trim().split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      
      // Check if this line marks the start of sideboard
      if (trimmed.toUpperCase().startsWith('SIDEBOARD:')) {
        isSideboard = true;
        // Extract card name if it's on the same line (e.g., "SIDEBOARD: 1 Wrath of God")
        const afterSideboard = trimmed.substring(trimmed.indexOf(':') + 1).trim();
        if (afterSideboard) {
          const match = afterSideboard.match(/^(\d+)?\s*(.+)$/);
          if (match) {
            const count = match[1] ? parseInt(match[1]) : 1;
            const cardName = match[2].trim();
            for (let i = 0; i < count; i++) {
              sideboardCards.push(cardName);
            }
          }
        }
        continue;
      }
      
      const match = trimmed.match(/^(\d+)?\s*(.+)$/);
      if (match) {
        const count = match[1] ? parseInt(match[1]) : 1;
        const cardName = match[2].trim();
        const targetArray = isSideboard ? sideboardCards : mainCards;
        for (let i = 0; i < count; i++) {
          targetArray.push(cardName);
        }
      }
    }
    return { deckCards: mainCards, sideboardCards };
  }, [deckText]);

  // Auto-fetch missing cards when they're added to the deck
  useEffect(() => {
    if (!showDeckModal || (deckCards.length === 0 && sideboardCards.length === 0)) return;
    
    // Get unique card names from deck and sideboard
    const uniqueCardNames = Array.from(new Set([...deckCards, ...sideboardCards]));
    
    // Find cards that are missing from database
    const missingCards = uniqueCardNames.filter(cardName => {
      // Skip if already fetched or currently fetching
      if (fetchedCards.has(cardName.toLowerCase()) || fetchingCards.has(cardName.toLowerCase())) {
        return false;
      }
      
      // Check if card exists in database (case-insensitive)
      const cardNameLower = cardName.toLowerCase();
      const exists = allCardNames.some(dbName => dbName.toLowerCase() === cardNameLower);
      return !exists;
    });
    
    if (missingCards.length === 0) return;
    
    // Fetch missing cards one by one
    const fetchMissingCards = async () => {
      for (const cardName of missingCards) {
        const cardNameLower = cardName.toLowerCase();
        
        // Mark as fetching
        setFetchingCards(prev => new Set(prev).add(cardNameLower));
        
        try {
          const trimmedName = cardName.trim();
          console.log(`🔄 Auto-fetching missing card: "${trimmedName}"`);
          const response = await fetch(`${API_BASE}/cards/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cardName: trimmedName })
          });
          console.log(`🔄 Auto-fetch response status: ${response.status} ${response.statusText}`);
          
          const data = await response.json();
          console.log(`🔄 Auto-fetch response data:`, data);
          
          if (data.success) {
            console.log(`✅ Auto-fetched: ${data.card?.name || trimmedName}`);
            // Reload database to get the new card
            await reload();
            // Mark as fetched
            setFetchedCards(prev => new Set(prev).add(cardNameLower));
          } else {
            const errorMsg = data.detail || data.error || 'Unknown error';
            console.warn(`⚠️ Failed to auto-fetch "${trimmedName}":`, errorMsg);
            // Mark as fetched (failed) to prevent endless retries
            setFetchedCards(prev => new Set(prev).add(cardNameLower));
          }
        } catch (err) {
          console.error(`❌ Error auto-fetching "${cardName}":`, err);
          if (err instanceof Error) {
            console.error(`❌ Error details:`, err.message, err.stack);
          }
          // Mark as fetched (failed) to prevent endless retries
          setFetchedCards(prev => new Set(prev).add(cardNameLower));
        } finally {
          // Remove from fetching set
          setFetchingCards(prev => {
            const next = new Set(prev);
            next.delete(cardNameLower);
            return next;
          });
        }
        
        // Small delay between fetches to be nice to the API
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    };
    
    fetchMissingCards();
  }, [deckCards, database, showDeckModal, allCardNames, fetchedCards, fetchingCards, reload]);

  const handleAddCard = async (cardName: string, count: number = 1, needsFetch: boolean = false) => {
    // If card is from Scryfall and not in local database, fetch it first
    if (needsFetch) {
      setIsFetching(true);
      try {
        const response = await fetch(`${API_BASE}/cards/fetch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cardName: cardName.trim() })
        });
        
        const data = await response.json();
        if (data.success) {
          // Reload database to get the new card
          await reload();
          // Now add to deck with the actual fetched name
          const fetchedName = data.card.name;
          const newLine = `${count} ${fetchedName}`;
          setDeckText(prev => {
            const trimmed = prev.trim();
            return trimmed ? `${trimmed}\n${newLine}` : newLine;
          });
          setCardSearchTerm('');
          setShowSuggestions(false);
          setScryfallSuggestions([]);
        } else {
          alert(`Failed to fetch card: ${data.detail || 'Unknown error'}`);
        }
      } catch (err) {
        console.error('Error fetching card:', err);
        alert('Error connecting to server');
      } finally {
        setIsFetching(false);
      }
    } else {
      // Card is already in local database, just add it
      const newLine = `${count} ${cardName}`;
      setDeckText(prev => {
        const trimmed = prev.trim();
        return trimmed ? `${trimmed}\n${newLine}` : newLine;
      });
      setCardSearchTerm('');
      setShowSuggestions(false);
      setScryfallSuggestions([]);
    }
  };

  const handleFetchCard = async () => {
    if (!searchCardName.trim()) return;
    
    setIsFetching(true);
    const cardName = searchCardName.trim();
    console.log(`🔍 Manual fetch requested for: "${cardName}"`);
    try {
      const response = await fetch(`${API_BASE}/cards/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cardName })
      });
      console.log(`🔍 Manual fetch response status: ${response.status} ${response.statusText}`);
      
      const data = await response.json();
      console.log(`🔍 Manual fetch response data:`, data);
      
      if (data.success) {
        console.log(`✅ Successfully fetched: "${data.card?.name || cardName}"`);
        // Mark as fetched BEFORE reloading to trigger cache busting
        const fetchedCardName = (data.card?.name || cardName).toLowerCase();
        setFetchedCards(prev => new Set(prev).add(fetchedCardName));
        // Reload database to get the new card
        await reload();
        // Add to deck list with specified count
        handleAddCard(data.card.name, searchCount);
        // Force a small delay to ensure file is written and available
        await new Promise(resolve => setTimeout(resolve, 200));
      } else {
        const errorMsg = data.detail || data.error || 'Unknown error';
        console.error(`❌ Failed to fetch "${cardName}":`, errorMsg);
        alert(`Failed to fetch card: ${errorMsg}`);
      }
    } catch (err) {
      console.error(`❌ Error fetching "${cardName}":`, err);
      if (err instanceof Error) {
        console.error(`❌ Error details:`, err.message, err.stack);
      }
      alert('Error connecting to server');
    } finally {
      setIsFetching(false);
    }
  };

  // Load username from localStorage on mount
  useEffect(() => {
    const savedName = localStorage.getItem('mtg_user_name');
    if (savedName) {
      setUserName(savedName);
    }
  }, []);

  // Save username to localStorage when it changes
  const handleUserNameChange = (name: string) => {
    setUserName(name);
    localStorage.setItem('mtg_user_name', name);
  };

  const fetchGames = async () => {
    try {
      const response = await fetch(`${API_BASE}/games`);
      const data = await response.json();
      if (data.success) {
        setGames(data.games);
      }
    } catch (err) {
      console.error('Failed to fetch games:', err);
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGames();
    // Refresh games list every 3 seconds
    const interval = setInterval(fetchGames, 3000);
    return () => clearInterval(interval);
  }, []);

  // Handle ESC key to close modals
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showDeckModal) {
          setShowDeckModal(false);
        } else if (showCreateForm) {
          setShowCreateForm(false);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showDeckModal, showCreateForm]);

  const handleCreateGame = async () => {
    if (!gameName.trim()) {
      setError('Please enter a game name');
      return;
    }

    if (!userName.trim()) {
      setError('Please enter your name at the top');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/games`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gameName: gameName.trim(),
          playerName: userName.trim(),
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        // HTTP error (400, 404, etc.)
        setError(data.detail || 'Failed to create game');
        return;
      }
      
      if (data.success) {
        // Save player ID to localStorage
        localStorage.setItem('mtg_player_id', data.playerId);
        localStorage.setItem('mtg_game_id', data.gameId);
        // Navigate to game
        onJoinGame(data.gameId, data.playerId);
      } else {
        setError(data.detail || 'Failed to create game');
      }
    } catch (err: any) {
      console.error('Failed to create game:', err);
      setError('Failed to connect to server');
    }
  };

  const handleJoinGame = async (gameId: string) => {
    if (!userName.trim()) {
      setError('Please enter your name at the top before joining');
      return;
    }

    // Check if we're rejoining a game we already have a player ID for
    const storedGameId = localStorage.getItem('mtg_game_id');
    const storedPlayerId = localStorage.getItem('mtg_player_id');
    
    if (storedGameId === gameId && storedPlayerId) {
      // Rejoin with existing player ID
      console.log('🔄 Rejoining game with existing player ID:', storedPlayerId);
      onJoinGame(gameId, storedPlayerId);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playerName: userName.trim(),
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        // HTTP error (400, 404, etc.)
        setError(data.detail || 'Failed to join game');
        return;
      }
      
      if (data.success) {
        // Save player ID to localStorage
        localStorage.setItem('mtg_player_id', data.playerId);
        localStorage.setItem('mtg_game_id', gameId);
        // Navigate to game
        onJoinGame(gameId, data.playerId);
      } else {
        setError(data.error || data.detail || 'Failed to join game');
      }
    } catch (err) {
      console.error('Failed to join game:', err);
      setError('Failed to connect to server');
    }
  };

  const handleDeleteGame = async (gameId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm('Delete this game? This cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/games/${gameId}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      if (data.success) {
        // Refresh games list
        fetchGames();
      } else {
        setError('Failed to delete game');
      }
    } catch (err) {
      console.error('Failed to delete game:', err);
      setError('Failed to delete game');
    }
  };

  const handleSaveDeck = async () => {
    if (!deckName.trim()) {
      setError('Please enter a deck name');
      return;
    }

    if (!deckText.trim()) {
      setError('Please enter deck cards');
      return;
    }

    // Parse deck text into format, splitting main deck and sideboard
    const lines = deckText.trim().split('\n');
    const mainCards: string[] = [];
    const sideboardCards: string[] = [];
    let isSideboard = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      // Check if this line marks the start of sideboard
      if (trimmed.toUpperCase().startsWith('SIDEBOARD:')) {
        isSideboard = true;
        // Extract card name if it's on the same line (e.g., "SIDEBOARD: 1 Wrath of God")
        const afterSideboard = trimmed.substring(trimmed.indexOf(':') + 1).trim();
        if (afterSideboard) {
          const match = afterSideboard.match(/^(\d+)?\s*(.+)$/);
          if (match) {
            const count = match[1] ? parseInt(match[1]) : 1;
            const cardName = match[2].trim();
            for (let i = 0; i < count; i++) {
              sideboardCards.push(cardName);
            }
          }
        }
        continue;
      }

      // Support formats: "4 Lightning Bolt" or "Lightning Bolt"
      const match = trimmed.match(/^(\d+)?\s*(.+)$/);
      if (match) {
        const count = match[1] ? parseInt(match[1]) : 1;
        const cardName = match[2].trim();
        const targetArray = isSideboard ? sideboardCards : mainCards;
        
        for (let i = 0; i < count; i++) {
          targetArray.push(cardName);
        }
      }
    }

    if (mainCards.length === 0 && sideboardCards.length === 0) {
      setError('Please enter at least one card');
      return;
    }

    try {
      // Save to backend as actual file
      const response = await fetch(`${API_BASE}/decks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: deckName.trim(),
          cards: mainCards,
          sideboard: sideboardCards
        }),
      });

      const data = await response.json();
      if (data.success) {
        console.log('✅ Deck saved:', data);
        const sideboardMsg = data.sideboard_count > 0 ? `\n${data.sideboard_count} sideboard cards` : '';
        alert(`Deck "${data.deck_name}" saved successfully!\n${data.card_count} main deck cards${sideboardMsg} saved to ${data.filename}`);
        setShowDeckModal(false);
        setDeckName('');
        setDeckText('');
        setError(null);
      } else {
        setError('Failed to save deck');
      }
    } catch (err) {
      console.error('Failed to save deck:', err);
      setError('Failed to save deck to server');
    }
  };

  return (
    <div
      className="min-h-screen overflow-y-auto bg-[#1a0a0a]"
      style={{
        background: 'linear-gradient(135deg, #1a0a0a 0%, #3c0f0f 50%, #1a0a0a 100%)',
        height: '100vh', // Ensure the container takes full height
        position: 'relative'
      }}
    >
      <div className="absolute inset-0 overflow-y-auto py-8 px-4">
      <div
          className="max-w-4xl w-full mx-auto p-8 rounded-xl"
        style={{
          background: 'linear-gradient(135deg, rgba(74, 55, 40, 0.9) 0%, rgba(58, 39, 24, 0.95) 100%)',
          border: '3px solid transparent',
          borderImage: 'linear-gradient(135deg, rgba(212, 179, 107, 0.6) 0%, rgba(139, 0, 0, 0.4) 50%, rgba(212, 179, 107, 0.6) 100%) 1',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.8), inset 0 2px 4px rgba(212, 179, 107, 0.2)',
            marginBottom: '40px' // Add margin bottom to ensure space for scrolling past
        }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <h1
            className="text-5xl font-bold mb-2"
            style={{
              background: 'linear-gradient(135deg, #d4b36b 0%, #f4d589 50%, #d4b36b 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '0 4px 8px rgba(0, 0, 0, 0.5)',
              letterSpacing: '0.1em',
            }}
          >
            MAGIC WORKSTATION
          </h1>
          <div className="flex justify-center gap-2 mb-4">
            {/* White Mana */}
            <div className="mana-symbol mana-white">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <circle cx="50" cy="50" r="18" fill="currentColor"/>
                <path d="M50 15 L55 35 L50 32 L45 35 Z" fill="currentColor"/>
                <path d="M72 28 L60 43 L63 40 L67 44 Z" fill="currentColor"/>
                <path d="M85 50 L65 55 L68 50 L65 45 Z" fill="currentColor"/>
                <path d="M72 72 L67 56 L63 60 L60 57 Z" fill="currentColor"/>
                <path d="M50 85 L45 65 L50 68 L55 65 Z" fill="currentColor"/>
                <path d="M28 72 L40 57 L37 60 L33 56 Z" fill="currentColor"/>
                <path d="M15 50 L35 45 L32 50 L35 55 Z" fill="currentColor"/>
                <path d="M28 28 L33 44 L37 40 L40 43 Z" fill="currentColor"/>
              </svg>
            </div>
            
            {/* Blue Mana */}
            <div className="mana-symbol mana-blue">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <path d="M50 15 Q35 25 35 45 Q35 60 40 70 Q45 80 50 85 Q55 80 60 70 Q65 60 65 45 Q65 25 50 15 Z" fill="currentColor"/>
                <ellipse cx="50" cy="78" rx="8" ry="5" fill="currentColor" opacity="0.6"/>
              </svg>
            </div>
            
            {/* Black Mana */}
            <div className="mana-symbol mana-black">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <ellipse cx="50" cy="35" rx="22" ry="28" fill="currentColor"/>
                <ellipse cx="35" cy="32" rx="9" ry="11" fill="none" stroke="currentColor" strokeWidth="14"/>
                <ellipse cx="65" cy="32" rx="9" ry="11" fill="none" stroke="currentColor" strokeWidth="14"/>
                <path d="M35 50 Q42 52 42 58 L38 58 Q38 54 32 52 Z" fill="currentColor"/>
                <path d="M65 50 Q58 52 58 58 L62 58 Q62 54 68 52 Z" fill="currentColor"/>
                <rect x="42" y="55" width="5" height="16" rx="2" fill="currentColor"/>
                <rect x="53" y="55" width="5" height="16" rx="2" fill="currentColor"/>
                <rect x="46" y="58" width="8" height="20" rx="2" fill="currentColor"/>
                <path d="M45 75 L40 82 L45 78 L50 85 L55 78 L60 82 L55 75 Z" fill="currentColor"/>
              </svg>
            </div>
            
            {/* Red Mana */}
            <div className="mana-symbol mana-red">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <path d="M50 25 Q45 30 42 38 Q40 45 38 52 Q36 60 40 68 Q42 72 46 72 Q48 72 50 68 Q52 72 54 72 Q58 72 60 68 Q64 60 62 52 Q60 45 58 38 Q55 30 50 25 Z" fill="currentColor"/>
                <path d="M35 45 Q32 50 30 56 Q28 62 30 68 Q32 72 36 70 Q38 68 38 64 Q38 58 40 52 Q38 50 35 45 Z" fill="currentColor"/>
                <path d="M65 45 Q68 50 70 56 Q72 62 70 68 Q68 72 64 70 Q62 68 62 64 Q62 58 60 52 Q62 50 65 45 Z" fill="currentColor"/>
                <path d="M42 35 Q38 38 35 42 Q33 46 34 50 Q36 48 38 46 Q40 42 42 38 Z" fill="currentColor"/>
                <path d="M58 35 Q62 38 65 42 Q67 46 66 50 Q64 48 62 46 Q60 42 58 38 Z" fill="currentColor"/>
              </svg>
            </div>
            
            {/* Green Mana */}
            <div className="mana-symbol mana-green">
              <svg viewBox="0 0 100 100" className="w-8 h-8">
                <rect x="46" y="55" width="8" height="30" fill="currentColor"/>
                <ellipse cx="32" cy="38" rx="16" ry="18" fill="currentColor"/>
                <ellipse cx="50" cy="32" rx="18" ry="20" fill="currentColor"/>
                <ellipse cx="68" cy="38" rx="16" ry="18" fill="currentColor"/>
                <ellipse cx="26" cy="52" rx="12" ry="14" fill="currentColor"/>
                <ellipse cx="74" cy="52" rx="12" ry="14" fill="currentColor"/>
                <ellipse cx="42" cy="50" rx="10" ry="12" fill="currentColor"/>
                <ellipse cx="58" cy="50" rx="10" ry="12" fill="currentColor"/>
                <path d="M38 70 Q35 75 32 80 L38 78 Q40 75 42 72 Z" fill="currentColor"/>
                <path d="M62 70 Q65 75 68 80 L62 78 Q60 75 58 72 Z" fill="currentColor"/>
              </svg>
            </div>
          </div>

          {/* Your Name Field - Hidden when deck modal is open */}
          {!showDeckModal && (
          <div className="mt-6 max-w-md mx-auto">
            <label className="block text-sm font-bold mb-2 text-center" style={{ color: '#d4b36b' }}>
              Your Name
            </label>
            <input
              type="text"
              value={userName}
              onChange={(e) => handleUserNameChange(e.target.value)}
              className="w-full px-4 py-3 rounded-lg text-center text-lg font-semibold bg-fantasy-dark/50 border-2 border-fantasy-gold/40 text-fantasy-gold focus:border-fantasy-gold/80 focus:outline-none transition-all"
              placeholder="Enter your name..."
              style={{
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.5), inset 0 1px 2px rgba(212, 179, 107, 0.1)',
              }}
            />
          </div>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-500/50 rounded text-red-200 text-center">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        {!showCreateForm && !showDeckModal && (
          <div className="mb-6 flex gap-4 justify-center">
            <motion.button
              onClick={() => setShowCreateForm(true)}
              className="px-8 py-3 rounded-lg font-bold text-lg"
              style={{
                background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.8) 0%, rgba(21, 128, 61, 0.9) 100%)',
                border: '2px solid rgba(34, 197, 94, 0.5)',
                color: '#f0fdf4',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(34, 197, 94, 0.2)',
              }}
              whileHover={{
                scale: 1.05,
                boxShadow: '0 6px 16px rgba(34, 197, 94, 0.4), inset 0 1px 0 rgba(34, 197, 94, 0.3)',
              }}
              whileTap={{ scale: 0.95 }}
            >
              + Create New Game
            </motion.button>

            <motion.button
              onClick={() => setShowDeckModal(true)}
              className="px-8 py-3 rounded-lg font-bold text-lg"
              style={{
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.8) 0%, rgba(29, 78, 216, 0.9) 100%)',
                border: '2px solid rgba(59, 130, 246, 0.5)',
                color: '#dbeafe',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(59, 130, 246, 0.2)',
              }}
              whileHover={{
                scale: 1.05,
                boxShadow: '0 6px 16px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(59, 130, 246, 0.3)',
              }}
              whileTap={{ scale: 0.95 }}
            >
              + Create Deck
            </motion.button>
          </div>
        )}

        {/* Create Game Form */}
        {showCreateForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-6 rounded-lg"
            style={{
              background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.3) 0%, rgba(80, 0, 0, 0.4) 100%)',
              border: '2px solid rgba(212, 179, 107, 0.3)',
            }}
          >
            <h2 className="text-2xl font-bold mb-4" style={{ color: '#d4b36b' }}>
              Create New Game
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: '#d4b36b' }}>
                  Game Name
                </label>
                <input
                  type="text"
                  value={gameName}
                  onChange={(e) => setGameName(e.target.value)}
                  className="w-full px-4 py-2 rounded bg-fantasy-dark/50 border-2 border-fantasy-gold/30 text-fantasy-gold focus:border-fantasy-gold/60 focus:outline-none"
                  placeholder="My Awesome Game"
                />
              </div>
              <div className="flex gap-3">
                <motion.button
                  onClick={handleCreateGame}
                  className="flex-1 px-6 py-2 rounded-lg font-bold"
                  style={{
                    background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.8) 0%, rgba(21, 128, 61, 0.9) 100%)',
                    border: '2px solid rgba(34, 197, 94, 0.5)',
                    color: '#f0fdf4',
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Create
                </motion.button>
                <motion.button
                  onClick={() => {
                    setShowCreateForm(false);
                    setError(null);
                  }}
                  className="px-6 py-2 rounded-lg font-bold"
                  style={{
                    background: 'linear-gradient(135deg, rgba(107, 26, 26, 0.6) 0%, rgba(80, 0, 0, 0.7) 100%)',
                    border: '2px solid rgba(139, 0, 0, 0.4)',
                    color: '#d4b36b',
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Cancel
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Create Deck Modal */}
        {showDeckModal && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 rounded-lg flex flex-col"
            style={{
              background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.3) 0%, rgba(80, 0, 0, 0.4) 100%)',
              border: '2px solid rgba(212, 179, 107, 0.3)',
              maxHeight: '90vh',
            }}
          >
            <div className="p-6 pb-4 flex-shrink-0">
            <h2 className="text-2xl font-bold mb-4" style={{ color: '#d4b36b' }}>
              Create Custom Deck
            </h2>
            </div>
            <div className="px-6 overflow-y-auto flex-1 min-h-0" style={{ maxHeight: 'calc(90vh - 200px)' }}>
              <div className="space-y-4 pb-4">
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: '#d4b36b' }}>
                  Deck Name
                </label>
                <input
                  type="text"
                  value={deckName}
                  onChange={(e) => setDeckName(e.target.value)}
                  className="w-full px-4 py-2 rounded bg-fantasy-dark/50 border-2 border-fantasy-gold/30 text-fantasy-gold focus:border-fantasy-gold/60 focus:outline-none"
                  placeholder="My Red Deck"
                />
              </div>
              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: '#d4b36b' }}>
                  Deck List (one card per line)
                </label>
                
                <div className="text-xs mb-2" style={{ color: '#d4b36b', opacity: 0.7 }}>
                  Format: "4 Lightning Bolt" or just "Mountain" • Same format as plain text deck list on Moxfield.com
                </div>
                
                {/* Card Search Input */}
                <div className="relative mb-2">
                  <input
                    type="text"
                    value={cardSearchTerm}
                    onChange={(e) => {
                      setCardSearchTerm(e.target.value);
                      setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        if (localFilteredCards.length > 0) {
                          // Select the first local suggestion
                          handleAddCard(localFilteredCards[0], searchCount, false);
                        } else if (scryfallSuggestions.length > 0) {
                          // Select the first Scryfall suggestion (will fetch)
                          handleAddCard(scryfallSuggestions[0], searchCount, true);
                        } else if (searchCardName.trim()) {
                          // If no matches, trigger manual fetch
                          handleFetchCard();
                        }
                      }
                    }}
                    className="w-full px-4 py-2 rounded bg-fantasy-dark/50 border-2 border-fantasy-gold/30 text-fantasy-gold focus:border-fantasy-gold/60 focus:outline-none"
                    placeholder="Search for a card to add..."
                  />
                  
                  {/* Suggestions Dropdown */}
                  <AnimatePresence>
                    {showSuggestions && cardSearchTerm.trim() && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute z-50 w-full mt-1 rounded-lg overflow-hidden max-h-60 overflow-y-auto"
                        style={{
                          background: '#2a1a1a',
                          border: '1px solid rgba(212, 179, 107, 0.4)',
                          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)'
                        }}
                      >
                        {/* Local database cards */}
                        {localFilteredCards.map((cardName) => (
                          <button
                            key={cardName}
                            onClick={() => handleAddCard(cardName, searchCount, false)}
                            className="w-full px-4 py-2 text-left hover:bg-fantasy-gold/20 transition-colors flex items-center justify-between group"
                            style={{ color: '#d4b36b' }}
                          >
                            <div className="flex items-center gap-3">
                              {/* Card Preview Thumbnail */}
                              <div 
                                className="w-8 h-11 rounded overflow-hidden relative shadow-sm flex-shrink-0"
                                style={{ 
                                  background: '#1a0f0f',
                                  border: '1px solid rgba(212, 179, 107, 0.3)' 
                                }}
                              >
                                <img 
                                  src={getCardImagePaths(cardName)[0]} 
                                  alt=""
                                  className="w-full h-full object-cover"
                                  onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    // Try next image path if available, or hide/show fallback
                                    if (!target.dataset.triedFallback) {
                                      target.dataset.triedFallback = 'true';
                                      target.src = '/cards/card-back.jpg';
                                    }
                                  }}
                                />
                              </div>
                              <span>{cardName}</span>
                            </div>
                            <span className="text-xs opacity-0 group-hover:opacity-100 text-fantasy-gold/70">
                              Add {searchCount} {searchCount === 1 ? 'copy' : 'copies'}
                            </span>
                          </button>
                        ))}

                        {/* Scryfall suggestions (fetch on click) */}
                        {scryfallSuggestions.length > 0 && (
                          <>
                            {localFilteredCards.length > 0 && (
                              <div 
                                className="px-4 py-2 text-xs font-semibold"
                                style={{ 
                                  color: '#60a5fa',
                                  borderTop: '1px solid rgba(212, 179, 107, 0.2)',
                                  background: 'rgba(30, 41, 59, 0.2)'
                                }}
                              >
                                From Scryfall (will fetch):
                              </div>
                            )}
                            {scryfallSuggestions.map((cardName) => (
                              <button
                                key={cardName}
                                onClick={() => handleAddCard(cardName, searchCount, true)}
                                disabled={isFetching}
                                className="w-full px-4 py-2 text-left hover:bg-fantasy-gold/20 transition-colors flex items-center justify-between group"
                                style={{ 
                                  color: '#60a5fa',
                                  opacity: isFetching ? 0.5 : 1
                                }}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-lg">🌐</span>
                                  <span>{cardName}</span>
                                </div>
                                <span className="text-xs opacity-0 group-hover:opacity-100" style={{ color: '#60a5fa' }}>
                                  Fetch + Add {searchCount}x
                                </span>
                              </button>
                            ))}
                          </>
                        )}

                        {/* Loading indicator */}
                        {isLoadingScryfallSuggestions && (
                          <div className="px-4 py-2 text-xs text-center" style={{ color: '#8b7355' }}>
                            Searching Scryfall...
                          </div>
                        )}
                        
                        {/* Fetch Option - Always visible if search term exists */}
                        <button
                          onClick={handleFetchCard}
                          disabled={isFetching}
                          className="w-full px-4 py-3 text-left hover:bg-fantasy-gold/20 transition-colors flex items-center justify-center gap-2"
                          style={{ 
                            color: '#60a5fa',
                            borderTop: filteredCards.length > 0 ? '1px solid rgba(212, 179, 107, 0.2)' : 'none',
                            background: 'rgba(30, 41, 59, 0.3)'
                          }}
                        >
                          {isFetching ? (
                            <span>⏳ Fetching...</span>
                          ) : (
                            <span>🌐 Fetch "{searchCardName}" from Web ({searchCount}x)</span>
                          )}
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <textarea
                  value={deckText}
                  onChange={(e) => setDeckText(e.target.value)}
                  className="w-full px-4 py-2 rounded bg-fantasy-dark/50 border-2 border-fantasy-gold/30 text-fantasy-gold focus:border-fantasy-gold/60 focus:outline-none font-mono"
                  placeholder="4 Lightning Bolt&#10;4 Counterspell&#10;20 Mountain&#10;&#10;SIDEBOARD:&#10;2 Wrath of God&#10;1 Disenchant"
                  rows={12}
                  style={{
                    resize: 'vertical',
                    minHeight: '200px',
                  }}
                />
                
                {/* Card Visual Preview Grid */}
                {(deckCards.length > 0 || sideboardCards.length > 0) && (
                  <div className="mt-4">
                    <label className="block text-sm font-bold mb-2" style={{ color: '#d4b36b' }}>
                      Visual Preview ({deckCards.length} cards{sideboardCards.length > 0 ? `, ${sideboardCards.length} sideboard` : ''})
                    </label>
                    
                    {/* Main Deck */}
                    {deckCards.length > 0 && (
                      <div 
                        className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-1 p-2 rounded bg-fantasy-dark/30 border border-fantasy-gold/20 overflow-y-auto mb-4"
                        style={{ maxHeight: '200px' }}
                      >
                        {deckCards.map((cardName, i) => {
                        const cardNameLower = cardName.toLowerCase();
                        const isFetching = fetchingCards.has(cardNameLower);
                        const isFetched = fetchedCards.has(cardNameLower);
                        
                        // Try to find card in database by name
                        const cardMetadata = Object.values(database).find(card => 
                          card.name.toLowerCase() === cardNameLower
                        );
                        
                        // Use metadata image path if available, otherwise generate paths
                        const imagePaths = getCardImagePaths(
                          cardName,
                          cardMetadata?.set && cardMetadata.set !== 'UNK' ? cardMetadata.set : undefined
                        );
                        const primaryImagePath = cardMetadata?.image || imagePaths[0];
                        
                        // Add cache busting for recently fetched cards
                        const imageSrc = isFetched 
                          ? `${primaryImagePath}?t=${Date.now()}` 
                          : primaryImagePath;
                        
                        return (
                          <div 
                            key={`${cardName}-${i}-${isFetched ? 'fetched' : 'pending'}-${cardMetadata ? 'hasMeta' : 'noMeta'}`}
                            className="relative aspect-[2.5/3.5] rounded overflow-hidden group cursor-pointer"
                            title={cardName}
                          >
                            <img 
                              src={imageSrc}
                              alt={cardName}
                              className="w-full h-full object-cover transition-transform group-hover:scale-110"
                              loading="lazy"
                              onLoad={() => {
                                console.log(`✅ Image loaded successfully for "${cardName}": ${imageSrc}`);
                              }}
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                console.log(`🖼️ Visual preview image error for "${cardName}":`, {
                                  imageSrc,
                                  hasMetadata: !!cardMetadata,
                                  metadataImage: cardMetadata?.image,
                                  imagePaths,
                                  isFetched
                                });
                                
                                // Try next image path if available
                                const currentIndex = imagePaths.indexOf(primaryImagePath);
                                if (currentIndex < imagePaths.length - 1 && !target.dataset.triedNext) {
                                  target.dataset.triedNext = 'true';
                                  const nextPath = imagePaths[currentIndex + 1];
                                  console.log(`🖼️ Trying next path: ${nextPath}`);
                                  target.src = nextPath + '?t=' + Date.now();
                                  return;
                                }
                                
                                // If card has metadata OR was just fetched, reload database and retry
                                if ((cardMetadata || isFetched) && !target.dataset.reloaded) {
                                  target.dataset.reloaded = 'true';
                                  console.log(`🖼️ Card ${isFetched ? 'was just fetched' : 'has metadata'}, reloading database and retrying...`);
                                  
                                  // Reload database first, then retry
                                  reload().then(() => {
                                    // Wait a bit for file system/Vite to sync
                                    setTimeout(() => {
                                      // Re-query the database (it will be updated after reload)
                                      // Use the metadata we already have, or try paths
                                      if (cardMetadata?.image) {
                                        const retryPath = cardMetadata.image + '?t=' + Date.now() + '&retry=1';
                                        console.log(`🖼️ Retrying with metadata image path: ${retryPath}`);
                                        target.src = retryPath;
                                      } else {
                                        // Try all image paths with cache busting
                                        const allPaths = getCardImagePaths(
                                          cardName,
                                          cardMetadata?.set && cardMetadata.set !== 'UNK' ? cardMetadata.set : undefined
                                        );
                                        const nextPathIndex = imagePaths.indexOf(primaryImagePath) + 1;
                                        if (nextPathIndex < allPaths.length) {
                                          const retryPath = allPaths[nextPathIndex] + '?t=' + Date.now() + '&retry=1';
                                          console.log(`🖼️ Retrying with next path: ${retryPath}`);
                                          target.src = retryPath;
                                        } else {
                                          console.log(`🖼️ All paths exhausted, using fallback`);
                                          target.src = '/cards/card-back.jpg';
                                        }
                                      }
                                    }, 500); // Longer delay for file system sync
                                  });
                                  return;
                                }
                                
                                // Final fallback
                                if (!target.dataset.triedFallback) {
                                  target.dataset.triedFallback = 'true';
                                  target.src = '/cards/card-back.jpg';
                                }
                              }}
                            />
                            {/* Loading indicator */}
                            {isFetching && (
                              <div className="absolute top-0 left-0 bg-black/60 text-fantasy-gold text-xs px-1 rounded-br animate-spin">
                                ↻
              </div>
                            )}
                            {/* Success indicator - show briefly after fetch */}
                            {isFetched && (
                              <div className="absolute top-0 right-0 bg-green-500 text-white text-xs px-1 rounded-bl animate-pulse">
                                ✓
                              </div>
                            )}
                          </div>
                        );
                      })}
                      </div>
                    )}
                    
                    {/* Sideboard - Separated with vertical space */}
                    {sideboardCards.length > 0 && (
                      <>
                        <div className="h-4"></div>
                        <label className="block text-sm font-bold mb-2" style={{ color: '#d4b36b' }}>
                          Sideboard ({sideboardCards.length} cards)
                        </label>
                        <div 
                          className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-1 p-2 rounded bg-fantasy-dark/30 border border-fantasy-gold/20 overflow-y-auto"
                          style={{ maxHeight: '200px' }}
                        >
                          {sideboardCards.map((cardName, i) => {
                            const cardNameLower = cardName.toLowerCase();
                            const isFetching = fetchingCards.has(cardNameLower);
                            const isFetched = fetchedCards.has(cardNameLower);
                            
                            // Try to find card in database by name
                            const cardMetadata = Object.values(database).find(card => 
                              card.name.toLowerCase() === cardNameLower
                            );
                            
                            // Use metadata image path if available, otherwise generate paths
                            const imagePaths = getCardImagePaths(
                              cardName,
                              cardMetadata?.set && cardMetadata.set !== 'UNK' ? cardMetadata.set : undefined
                            );
                            const primaryImagePath = cardMetadata?.image || imagePaths[0];
                            
                            // Add cache busting for recently fetched cards
                            const imageSrc = isFetched 
                              ? `${primaryImagePath}?t=${Date.now()}` 
                              : primaryImagePath;
                            
                            return (
                              <div 
                                key={`sideboard-${cardName}-${i}-${isFetched ? 'fetched' : 'pending'}-${cardMetadata ? 'hasMeta' : 'noMeta'}`}
                                className="relative aspect-[2.5/3.5] rounded overflow-hidden group cursor-pointer"
                                title={cardName}
                              >
                                <img 
                                  src={imageSrc}
                                  alt={cardName}
                                  className="w-full h-full object-cover transition-transform group-hover:scale-110"
                                  loading="lazy"
                                  onLoad={() => {
                                    console.log(`✅ Image loaded successfully for "${cardName}": ${imageSrc}`);
                                  }}
                                  onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    console.log(`🖼️ Visual preview image error for "${cardName}":`, {
                                      imageSrc,
                                      hasMetadata: !!cardMetadata,
                                      metadataImage: cardMetadata?.image,
                                      imagePaths,
                                      isFetched
                                    });
                                    
                                    // Try next image path if available
                                    const currentIndex = imagePaths.indexOf(primaryImagePath);
                                    if (currentIndex < imagePaths.length - 1 && !target.dataset.triedNext) {
                                      target.dataset.triedNext = 'true';
                                      const nextPath = imagePaths[currentIndex + 1];
                                      console.log(`🖼️ Trying next path: ${nextPath}`);
                                      target.src = nextPath + '?t=' + Date.now();
                                      return;
                                    }
                                    
                                    // If card has metadata OR was just fetched, reload database and retry
                                    if ((cardMetadata || isFetched) && !target.dataset.reloaded) {
                                      target.dataset.reloaded = 'true';
                                      console.log(`🖼️ Card ${isFetched ? 'was just fetched' : 'has metadata'}, reloading database and retrying...`);
                                      
                                      // Reload database first, then retry
                                      reload().then(() => {
                                        // Wait a bit for file system/Vite to sync
                                        setTimeout(() => {
                                          // Re-query the database (it will be updated after reload)
                                          // Use the metadata we already have, or try paths
                                          if (cardMetadata?.image) {
                                            const retryPath = cardMetadata.image + '?t=' + Date.now() + '&retry=1';
                                            console.log(`🖼️ Retrying with metadata image path: ${retryPath}`);
                                            target.src = retryPath;
                                          } else {
                                            // Try all image paths with cache busting
                                            const allPaths = getCardImagePaths(
                                              cardName,
                                              cardMetadata?.set && cardMetadata.set !== 'UNK' ? cardMetadata.set : undefined
                                            );
                                            const nextPathIndex = imagePaths.indexOf(primaryImagePath) + 1;
                                            if (nextPathIndex < allPaths.length) {
                                              const retryPath = allPaths[nextPathIndex] + '?t=' + Date.now() + '&retry=1';
                                              console.log(`🖼️ Retrying with next path: ${retryPath}`);
                                              target.src = retryPath;
                                            } else {
                                              console.log(`🖼️ All paths exhausted, using fallback`);
                                              target.src = '/cards/card-back.jpg';
                                            }
                                          }
                                        }, 500); // Longer delay for file system sync
                                      });
                                      return;
                                    }
                                    
                                    // Final fallback
                                    if (!target.dataset.triedFallback) {
                                      target.dataset.triedFallback = 'true';
                                      target.src = '/cards/card-back.jpg';
                                    }
                                  }}
                                />
                                {/* Loading indicator */}
                                {isFetching && (
                                  <div className="absolute top-0 left-0 bg-black/60 text-fantasy-gold text-xs px-1 rounded-br animate-spin">
                                    ↻
                                  </div>
                                )}
                                {/* Success indicator - show briefly after fetch */}
                                {isFetched && (
                                  <div className="absolute top-0 right-0 bg-green-500 text-white text-xs px-1 rounded-bl animate-pulse">
                                    ✓
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
            </div>
            {/* Buttons - Always visible at bottom */}
            <div className="p-6 pt-4 flex gap-3 flex-shrink-0 border-t" style={{ borderColor: 'rgba(212, 179, 107, 0.2)' }}>
                <motion.button
                  onClick={handleSaveDeck}
                  className="flex-1 px-6 py-2 rounded-lg font-bold"
                  style={{
                    background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.8) 0%, rgba(21, 128, 61, 0.9) 100%)',
                    border: '2px solid rgba(34, 197, 94, 0.5)',
                    color: '#f0fdf4',
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Save Deck
                </motion.button>
                <motion.button
                  onClick={() => {
                    setShowDeckModal(false);
                    setDeckName('');
                    setDeckText('');
                    setError(null);
                  }}
                  className="px-6 py-2 rounded-lg font-bold"
                  style={{
                    background: 'linear-gradient(135deg, rgba(107, 26, 26, 0.6) 0%, rgba(80, 0, 0, 0.7) 100%)',
                    border: '2px solid rgba(139, 0, 0, 0.4)',
                    color: '#d4b36b',
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Cancel
                </motion.button>
            </div>
          </motion.div>
        )}

        {/* Games List */}
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: '#d4b36b' }}>
            Active Games
          </h2>

          {loading ? (
            <div className="text-center py-8" style={{ color: '#d4b36b' }}>
              Loading games...
            </div>
          ) : games.length === 0 ? (
            <div className="text-center py-8" style={{ color: '#d4b36b', opacity: 0.6 }}>
              No active games. Create one to get started!
            </div>
          ) : (
            <div 
              className="space-y-3 overflow-y-auto pr-2" 
              style={{ 
                maxHeight: '500px',
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(212, 179, 107, 0.5) rgba(74, 55, 40, 0.3)'
              }}
            >
              {games.map((game) => (
                <motion.div
                  key={game.game_id}
                  className="p-4 rounded-lg flex items-center gap-3"
                  style={{
                    background: 'linear-gradient(135deg, rgba(74, 55, 40, 0.6) 0%, rgba(58, 39, 24, 0.7) 100%)',
                    border: '2px solid rgba(212, 179, 107, 0.3)',
                  }}
                  whileHover={{
                    borderColor: 'rgba(212, 179, 107, 0.6)',
                    boxShadow: '0 4px 12px rgba(212, 179, 107, 0.2)',
                  }}
                >
                  {/* Delete button */}
                  <motion.button
                    onClick={(e) => handleDeleteGame(game.game_id, e)}
                    className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                    style={{
                      background: 'linear-gradient(135deg, rgba(139, 0, 0, 0.4) 0%, rgba(80, 0, 0, 0.5) 100%)',
                      border: '1px solid rgba(220, 38, 38, 0.4)',
                      color: '#ef4444',
                    }}
                    whileHover={{
                      scale: 1.1,
                      background: 'linear-gradient(135deg, rgba(153, 27, 27, 0.6) 0%, rgba(127, 29, 29, 0.7) 100%)',
                      borderColor: 'rgba(220, 38, 38, 0.6)',
                    }}
                    whileTap={{ scale: 0.9 }}
                  >
                    ✕
                  </motion.button>

                  {/* Game info */}
                  <div className="flex-1">
                    <h3 className="text-xl font-bold" style={{ color: '#d4b36b' }}>
                      {game.name}
                    </h3>
                    <div className="text-sm" style={{ color: '#d4b36b', opacity: 0.7 }}>
                      Players: {game.player_names.join(', ')} ({game.player_count}/2)
                    </div>
                  </div>

                  {/* Join/Rejoin/Full button */}
                  {(() => {
                    // Check if we have a stored player ID for this specific game
                    const storedGameId = localStorage.getItem('mtg_game_id');
                    const storedPlayerId = localStorage.getItem('mtg_player_id');
                    const canRejoin = storedGameId === game.game_id && storedPlayerId;
                    
                    // Also verify name matches (for display purposes)
                    const isPlayerInGame = game.player_names.some(name => 
                      name.toLowerCase() === userName.toLowerCase()
                    );

                    if (canRejoin && isPlayerInGame) {
                      // Show Rejoin button - user has valid session for THIS game
                      return (
                        <motion.button
                          onClick={() => handleJoinGame(game.game_id)}
                          className="flex-shrink-0 px-6 py-2 rounded-lg font-bold"
                          style={{
                            background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.8) 0%, rgba(21, 128, 61, 0.9) 100%)',
                            border: '2px solid rgba(34, 197, 94, 0.5)',
                            color: '#f0fdf4',
                          }}
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Rejoin Game
                        </motion.button>
                      );
                    } else if (game.player_count < 2) {
                      // Show Join button for available games
                      return (
                    <motion.button
                      onClick={() => handleJoinGame(game.game_id)}
                      className="flex-shrink-0 px-6 py-2 rounded-lg font-bold"
                      style={{
                        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.8) 0%, rgba(29, 78, 216, 0.9) 100%)',
                        border: '2px solid rgba(59, 130, 246, 0.5)',
                        color: '#dbeafe',
                      }}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      Join Game
                    </motion.button>
                      );
                    } else {
                      // Show Full for games at capacity
                      return (
                    <div
                      className="flex-shrink-0 px-6 py-2 rounded-lg font-bold"
                      style={{
                        background: 'rgba(107, 26, 26, 0.4)',
                        border: '2px solid rgba(139, 0, 0, 0.3)',
                        color: '#d4b36b',
                        opacity: 0.5,
                      }}
                    >
                      Full
                    </div>
                      );
                    }
                  })()}
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Copyright Disclaimer */}
        <div 
          className="mt-8 pt-6 border-t"
          style={{
            borderColor: 'rgba(212, 179, 107, 0.2)',
            textAlign: 'center'
          }}
        >
          <p 
            className="text-xs mb-2"
            style={{ 
              color: '#d4b36b',
              opacity: 0.7
            }}
          >
            Wizards of the Coast, Magic: The Gathering, and their logos are trademarks of Wizards of the Coast LLC in the United States and other countries. © 1993-2026 Wizards. All Rights Reserved.
          </p>
          <p 
            className="text-xs mb-2"
            style={{ 
              color: '#d4b36b',
              opacity: 0.7
            }}
          >
            Magic Workstation is not affiliated with, endorsed, sponsored, or specifically approved by Wizards of the Coast LLC. Magic Workstation may use the trademarks and other intellectual property of Wizards of the Coast LLC, which is permitted under Wizards' Fan Site Policy.
          </p>
          <p 
            className="text-xs"
            style={{ 
              color: '#d4b36b',
              opacity: 0.6,
              fontStyle: 'italic'
            }}
          >
            This is a non-commercial, educational project. No profit is made from this project.
          </p>
        </div>
        </div>
      </div>
      
      {/* Lobby Chat */}
      <LobbyChat userName={userName} />
    </div>
  );
};

export default Lobby;

