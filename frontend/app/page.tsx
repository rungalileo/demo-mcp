'use client';

import { useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import axios from 'axios';
import { format } from 'date-fns';

interface Call {
  id: string;
  title: string;
  start_time: string;
  duration: number;
  participants: string[];
}

interface BuyerAnalysis {
  call_id: string;
  title: string;
  date: string;
  intent: string;
  explanation: string;
  transcript: string;
}

export default function Home() {
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [calls, setCalls] = useState<Call[]>([]);
  const [selectedCall, setSelectedCall] = useState<string>('');
  const [analysis, setAnalysis] = useState<BuyerAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCalls = async (date: Date) => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.post('http://localhost:8000/calls', {
        date: format(date, 'yyyy-MM-dd')
      });
      setCalls(response.data.calls);
    } catch (err) {
      setError('Failed to fetch calls');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysis = async () => {
    if (!selectedCall || !selectedDate) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await axios.post('http://localhost:8000/analysis', {
        call_title: selectedCall,
        call_date: format(selectedDate, 'yyyy-MM-dd')
      });
      setAnalysis(response.data);
    } catch (err) {
      setError('Failed to fetch analysis');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (date: Date | null) => {
    setSelectedDate(date);
    setSelectedCall('');
    setAnalysis(null);
    if (date) {
      fetchCalls(date);
    }
  };

  const getIntentColor = (intent: string) => {
    switch (intent.toLowerCase()) {
      case 'very likely to buy':
        return 'bg-green-100 text-green-800';
      case 'likely to buy':
        return 'bg-green-50 text-green-700';
      case 'neutral':
        return 'bg-gray-100 text-gray-800';
      case 'unsure':
        return 'bg-yellow-100 text-yellow-800';
      case 'less likely to buy':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Gong Call Analyzer</h1>
        
        <div className="space-y-6">
          {/* Date Picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Date
            </label>
            <DatePicker
              selected={selectedDate}
              onChange={handleDateChange}
              className="w-full p-2 border border-gray-300 rounded-md"
              dateFormat="yyyy-MM-dd"
              placeholderText="Select a date"
            />
          </div>

          {/* Call Selection */}
          {calls.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Call
              </label>
              <select
                value={selectedCall}
                onChange={(e) => setSelectedCall(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md"
              >
                <option value="">Select a call</option>
                {calls.map((call) => (
                  <option key={call.id} value={call.title}>
                    {call.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Get Analysis Button */}
          {selectedCall && (
            <button
              onClick={fetchAnalysis}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-blue-300"
            >
              {loading ? 'Loading...' : 'Get Buyer Analysis'}
            </button>
          )}

          {/* Error Message */}
          {error && (
            <div className="text-red-600 bg-red-50 p-4 rounded-md">
              {error}
            </div>
          )}

          {/* Analysis Display */}
          {analysis && (
            <div className="mt-8">
              <h2 className="text-2xl font-semibold mb-4">Buyer Analysis</h2>
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-xl font-medium mb-2">{analysis.title}</h3>
                <p className="text-gray-600 mb-4">{analysis.date}</p>
                
                {/* Intent Badge */}
                <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-6 ${getIntentColor(analysis.intent)}`}>
                  {analysis.intent}
                </div>

                {/* Explanation */}
                <div className="prose max-w-none">
                  {analysis.explanation.split('\n').map((paragraph, index) => (
                    <p key={index} className="mb-4">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
} 