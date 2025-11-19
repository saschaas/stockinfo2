import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard/Dashboard'
import StockResearch from './components/StockResearch/StockResearch'
import FundTracker from './components/FundTracker/FundTracker'
import ConfigWizard from './components/ConfigWizard/ConfigWizard'
import Layout from './components/Layout/Layout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="research" element={<StockResearch />} />
          <Route path="funds" element={<FundTracker />} />
          <Route path="config" element={<ConfigWizard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
