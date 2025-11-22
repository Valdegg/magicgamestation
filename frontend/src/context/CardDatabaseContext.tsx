import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { CardDatabase, loadCardDatabase, getCardMetadata, CardMetadata } from '../utils/cardDatabase';

interface CardDatabaseContextType {
  database: CardDatabase;
  isLoading: boolean;
  error: string | null;
  getCard: (cardId: string) => CardMetadata | null;
  reload: () => Promise<void>;
}

const CardDatabaseContext = createContext<CardDatabaseContextType | undefined>(undefined);

export const CardDatabaseProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [database, setDatabase] = useState<CardDatabase>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDatabase = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const db = await loadCardDatabase();
      setDatabase(db);
      console.log(`Loaded ${Object.keys(db).length} cards from database`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load card database';
      setError(errorMessage);
      console.error('Card database error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDatabase();
  }, []);

  const getCard = (cardId: string): CardMetadata | null => {
    return getCardMetadata(database, cardId);
  };

  const value: CardDatabaseContextType = {
    database,
    isLoading,
    error,
    getCard,
    reload: loadDatabase,
  };

  return (
    <CardDatabaseContext.Provider value={value}>
      {children}
    </CardDatabaseContext.Provider>
  );
};

export const useCardDatabase = () => {
  const context = useContext(CardDatabaseContext);
  if (!context) {
    throw new Error('useCardDatabase must be used within CardDatabaseProvider');
  }
  return context;
};

