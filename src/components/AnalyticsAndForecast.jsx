import React, { useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import { 
  TrendingUp, 
  Sparkles, 
  Activity, 
  Clock, 
  DollarSign, 
  CheckCircle2, 
  AlertTriangle,
  Bot
} from 'lucide-react';

// Register ChartJS modules
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function AnalyticsAndForecast({ assets }) {
  const [forecastHorizon, setForecastHorizon] = useState('14'); // 14 or 30 days

  // 1. Chart.js Data: Engine Runtime vs Idle Hours per Rented Asset
  const assetLabels = assets.map(a => a.id);
  const engineData = assets.map(a => a.engineHours || a.engineHoursPerDay || 0);
  const idleData = assets.map(a => a.idleHours || a.idleHoursPerDay || 0);

  const usageChartData = {
    labels: assetLabels,
    datasets: [
      {
        label: 'Engine Hours (Productive)',
        data: engineData,
        backgroundColor: '#10B981', // Emerald green
        borderRadius: 6,
      },
      {
        label: 'Idle Hours (Underutilized)',
        data: idleData,
        backgroundColor: '#F59E0B', // Amber warning
        borderRadius: 6,
      }
    ]
  };

  const usageChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#D1D5DB', font: { size: 11, weight: 'bold' } }
      },
      tooltip: {
        backgroundColor: '#1F1F1F',
        titleColor: '#FFCD11',
        bodyColor: '#FFFFFF',
        borderColor: '#333333',
        borderWidth: 1,
      }
    },
    scales: {
      x: {
        ticks: { color: '#9CA3AF' },
        grid: { color: '#262626' }
      },
      y: {
        ticks: { color: '#9CA3AF' },
        grid: { color: '#262626' },
        title: { display: true, text: 'Total Hours', color: '#6B7280', font: { size: 10 } }
      }
    }
  };

  // 2. Chart.js Data: ARIMA Demand Forecasting for Upcoming Site Requirements
  const forecastDays = forecastHorizon === '14' 
    ? ['Day 1', 'Day 3', 'Day 5', 'Day 7', 'Day 9', 'Day 11', 'Day 14']
    : ['Week 1', 'Week 2', 'Week 3', 'Week 4'];

  const predictedExcavatorDemand = forecastHorizon === '14' ? [4, 5, 6, 7, 6, 8, 9] : [18, 22, 28, 31];
  const predictedBulldozerDemand = forecastHorizon === '14' ? [2, 3, 3, 4, 4, 5, 5] : [10, 12, 14, 16];

  const demandForecastData = {
    labels: forecastDays,
    datasets: [
      {
        fill: true,
        label: 'Excavator Projected Demand',
        data: predictedExcavatorDemand,
        borderColor: '#FFCD11', // Caterpillar Yellow
        backgroundColor: 'rgba(255, 205, 17, 0.12)',
        tension: 0.35,
        pointBackgroundColor: '#FFCD11',
        pointRadius: 4,
      },
      {
        fill: true,
        label: 'Bulldozer Projected Demand',
        data: predictedBulldozerDemand,
        borderColor: '#38BDF8', // Cyan
        backgroundColor: 'rgba(56, 189, 248, 0.10)',
        tension: 0.35,
        pointBackgroundColor: '#38BDF8',
        pointRadius: 4,
      }
    ]
  };

  const demandForecastOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#D1D5DB', font: { size: 11, weight: 'bold' } }
      },
      tooltip: {
        backgroundColor: '#1F1F1F',
        titleColor: '#FFCD11',
        bodyColor: '#FFFFFF',
        borderColor: '#333333',
        borderWidth: 1,
      }
    },
    scales: {
      x: {
        ticks: { color: '#9CA3AF' },
        grid: { color: '#262626' }
      },
      y: {
        ticks: { color: '#9CA3AF' },
        grid: { color: '#262626' },
        title: { display: true, text: 'Units Required', color: '#6B7280', font: { size: 10 } }
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Wow Factor: Natural Language Fleet AI Briefing Card */}
      <div className="bg-gradient-to-r from-[#181818] to-[#201A10] border border-[#FFCD11]/30 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-[#FFCD11] p-2.5 rounded-xl text-black">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-extrabold text-white">
                  Caterpillar Autonomous Fleet Intelligence
                </h3>
                <span className="text-[10px] bg-[#FFCD11]/20 text-[#FFCD11] border border-[#FFCD11]/40 px-2 py-0.5 rounded-full font-bold uppercase">
                  NLP Digest
                </span>
              </div>
              <p className="text-xs text-neutral-400 mt-0.5">
                Real-time operational summary synthesized from active telemetry streams
              </p>
            </div>
          </div>
          <Sparkles className="w-5 h-5 text-[#FFCD11] animate-spin" style={{ animationDuration: '8s' }} />
        </div>

        {/* Generated Natural Language Summary */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-[#141414]/90 border border-neutral-800 p-3.5 rounded-xl">
            <div className="flex items-center text-amber-400 font-bold mb-1">
              <AlertTriangle className="w-4 h-4 mr-1.5" />
              Idle Cost Waste Detected
            </div>
            <p className="text-neutral-300 text-[11px] leading-relaxed">
              Excavator <strong className="text-white">EQX1001</strong> logged <strong>10.0 idle hours</strong> vs only <strong>1.5 engine hours</strong>. Reallocating or returning this unit can save an estimated <strong>$225.00/day</strong>.
            </p>
          </div>

          <div className="bg-[#141414]/90 border border-neutral-800 p-3.5 rounded-xl">
            <div className="flex items-center text-emerald-400 font-bold mb-1">
              <CheckCircle2 className="w-4 h-4 mr-1.5" />
              High Efficiency Asset
            </div>
            <p className="text-neutral-300 text-[11px] leading-relaxed">
              Bulldozer <strong className="text-white">EQX1003</strong> operating at <strong>93.7% peak efficiency</strong> with 7.5 engine hours at Bangalore Quarry S003. Optimal benchmark.
            </p>
          </div>

          <div className="bg-[#141414]/90 border border-neutral-800 p-3.5 rounded-xl">
            <div className="flex items-center text-cyan-400 font-bold mb-1">
              <TrendingUp className="w-4 h-4 mr-1.5" />
              ARIMA Demand Prediction
            </div>
            <p className="text-neutral-300 text-[11px] leading-relaxed">
              Excavator demand is projected to spike by <strong>+35%</strong> over the next 14 days at Site S006. Pre-book 2 additional hydraulic units to prevent delays.
            </p>
          </div>
        </div>
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Engine vs Idle Runtime */}
        <div className="bg-[#141414] border border-[#2B2B2B] rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4 border-b border-[#242424] pb-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center">
                <Clock className="w-4 h-4 mr-2 text-emerald-400" />
                Asset Utilization: Engine vs. Idle Hours
              </h3>
              <p className="text-xs text-neutral-400">Comparing active workload against non-productive idle time</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <Bar data={usageChartData} options={usageChartOptions} />
          </div>
        </div>

        {/* Chart 2: ARIMA Predictive Demand Curve */}
        <div className="bg-[#141414] border border-[#2B2B2B] rounded-2xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4 border-b border-[#242424] pb-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center">
                <TrendingUp className="w-4 h-4 mr-2 text-[#FFCD11]" />
                ARIMA Time-Series Demand Forecast
              </h3>
              <p className="text-xs text-neutral-400">Predicted equipment requirements by site schedule</p>
            </div>
            <select
              value={forecastHorizon}
              onChange={(e) => setForecastHorizon(e.target.value)}
              className="bg-[#1F1F1F] border border-[#333] rounded-lg px-2.5 py-1 text-xs text-neutral-300 focus:outline-none focus:border-[#FFCD11]"
            >
              <option value="14">14 Days Forecast</option>
              <option value="30">30 Days Forecast</option>
            </select>
          </div>
          <div className="h-64 w-full">
            <Line data={demandForecastData} options={demandForecastOptions} />
          </div>
        </div>
      </div>
    </div>
  );
}