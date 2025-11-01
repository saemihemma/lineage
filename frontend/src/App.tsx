import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { BriefingScreen } from './screens/BriefingScreen';
import { LoadingScreen } from './screens/LoadingScreen';
import { SimulationScreen } from './screens/SimulationScreen';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/briefing" replace />} />
        <Route path="/briefing" element={<BriefingScreen />} />
        <Route path="/loading" element={<LoadingScreen />} />
        <Route path="/simulation" element={<SimulationScreen />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
