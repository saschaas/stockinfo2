import { Outlet, Link, useLocation } from 'react-router-dom'

export default function Layout() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/research', label: 'Stock Research', icon: '🔍' },
    { path: '/funds', label: 'Fund Tracker', icon: '💼' },
    { path: '/config', label: 'Configuration', icon: '⚙️' },
    { path: '/overview', label: 'Overview', icon: '🔗' },
  ]

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white border-b border-border-warm sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              {/* Logo */}
              <div className="flex-shrink-0 flex items-center">
                <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center mr-3">
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h1 className="text-xl font-bold text-gray-900">
                  Stock<span className="text-primary-500">Info</span>
                </h1>
              </div>

              {/* Navigation */}
              <nav className="hidden sm:ml-10 sm:flex sm:space-x-2">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`
                        inline-flex items-center px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                        ${isActive
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-gray-600 hover:bg-cream-dark hover:text-gray-900'
                        }
                      `}
                    >
                      <span className="mr-2">{item.icon}</span>
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </div>

            {/* Right side - could add user menu, notifications, etc. */}
            <div className="flex items-center space-x-4">
              <button className="p-2 rounded-xl text-gray-500 hover:bg-cream-dark hover:text-gray-700 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile navigation */}
        <nav className="sm:hidden border-t border-border-warm">
          <div className="px-4 py-2 flex space-x-2 overflow-x-auto">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    inline-flex items-center px-3 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200
                    ${isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-cream-dark'
                    }
                  `}
                >
                  <span className="mr-1.5">{item.icon}</span>
                  {item.label}
                </Link>
              )
            })}
          </div>
        </nav>
      </header>

      {/* Main content */}
      <main className="max-w-[1600px] mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border-warm bg-white mt-auto">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-gray-500 text-center">
            AI-Powered Stock Research Tool • Data for informational purposes only
          </p>
        </div>
      </footer>
    </div>
  )
}
