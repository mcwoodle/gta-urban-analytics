import * as React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';

import { store } from './store';
import { MapShell } from './components/MapShell';

const Root = () => (
  <Provider store={store}>
    <MapShell />
  </Provider>
);

const container = document.getElementById('root');
if (!container) {
  throw new Error('No #root element in document — cannot mount the viz.');
}
const root = ReactDOM.createRoot(container);
root.render(<Root />);
