import DefaultTheme from 'vitepress/theme';
import Layout from './Layout.vue';
import HoloChart from './HoloChart.vue';
import './custom.css';
export default { extends: DefaultTheme, Layout, enhanceApp({ app }) { app.component('HoloChart', HoloChart); } };
