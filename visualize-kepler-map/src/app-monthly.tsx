import * as React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';

import { store } from './store';
import { MonthlyMapShell } from './components/MonthlyMapShell';

const Root = () => (
  <Provider store={store}>
    <MonthlyMapShell />
  </Provider>
);

const container = document.getElementById('root');
if (!container) {
  throw new Error('No #root element in document — cannot mount the monthly viz.');
}
const root = ReactDOM.createRoot(container);
root.render(<Root />);
