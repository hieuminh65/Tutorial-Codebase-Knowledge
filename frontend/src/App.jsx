// Updated App.jsx with modular imports
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import InputForm from './components/InputForm/InputForm';
import OutputDisplay from './components/OutputDisplay/OutputDisplay';
import './App.css';

// Main App Component with modular structure
function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<InputForm />} />
                <Route path="/output/:repoName" element={<OutputDisplay />} />
                <Route path="/output/:repoName/:lessonPath/*" element={<OutputDisplay />} />
                {/* Add other routes as needed */}
            </Routes>
        </Router>
    );
}

export default App;
