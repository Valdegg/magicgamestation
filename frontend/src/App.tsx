import { useState, useEffect } from 'react';
import { useGameState } from './context/GameStateWebSocket';
import Lobby from './components/Lobby';
import GameView from './components/GameView';

function App() {
  const [currentView, setCurrentView] = useState<'lobby' | 'game'>('lobby');
  const { initializeGame } = useGameState();

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    setCurrentView(urlParams.get('game') ? 'game' : 'lobby');
  }, []);

  const handleJoinGame = async (gameId: string, playerId: string) => {
    setCurrentView('game');
    const url = new URL(window.location.href);
    url.searchParams.set('game', gameId);
    url.searchParams.set('player', playerId);
    window.history.pushState({}, '', url);
    await initializeGame();
  };

  const handleBackToLobby = () => {
    setCurrentView('lobby');
    localStorage.removeItem('mtg_game_id');
    localStorage.removeItem('mtg_player_id');
    const url = new URL(window.location.href);
    url.search = '';
    window.history.pushState({}, '', url);
  };

  return currentView === 'lobby' 
    ? <Lobby onJoinGame={handleJoinGame} /> 
    : <GameView onBackToLobby={handleBackToLobby} />;
}

export default App;
