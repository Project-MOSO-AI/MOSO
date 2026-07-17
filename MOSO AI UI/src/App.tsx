import { NeuralBackground } from './components/shared/NeuralBackground';
import { TopNav } from './components/layout/TopNav';
import { StatusBar } from './components/layout/StatusBar';
import { LogPanel } from './components/panels/LogPanel';
import { AuraPanel } from './components/panels/AuraPanel';
import { ExplainerPanel } from './components/panels/ExplainerPanel';
import { useMosoApi } from './hooks/useMosoApi';
import './index.css';

function App() {
  const api = useMosoApi();

  return (
    <div className="w-screen h-screen flex flex-col bg-moso-bg overflow-hidden">
      <NeuralBackground />

      <TopNav status={api.status} systemStats={api.systemStats} />

      <div className="flex flex-1 min-h-0 relative z-10">
        <LogPanel
          logs={api.logs}
          searchQuery={api.searchQuery}
          onSearchChange={api.setSearchQuery}
          activeFilter={api.activeFilter}
          onFilterChange={api.setActiveFilter}
          onLogSelect={api.selectLog}
        />

        <AuraPanel
          messages={api.messages}
          isListening={api.isListening}
          isThinking={api.isThinking}
          activityFeed={api.activityFeed}
          onSendMessage={api.sendMessage}
          onToggleVoice={api.toggleVoice}
          onFileUpload={api.uploadFile}
          orbState={api.orbState}
        />

        <ExplainerPanel
          explanation={api.currentExplanation}
          selectedLog={api.selectedLog}
        />
      </div>

      <StatusBar
        memorySynced={api.memorySynced}
        localMode={api.localMode}
        offlineReady={api.offlineReady}
        encrypted={api.encrypted}
      />
    </div>
  );
}

export default App;
