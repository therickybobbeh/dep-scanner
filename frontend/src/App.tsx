import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ScanPage from './pages/ScanPage';
import ReportPage from './pages/ReportPage';
import Header from './components/Header';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/scan" element={<ScanPage />} />
            <Route path="/report/:jobId" element={<ReportPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;