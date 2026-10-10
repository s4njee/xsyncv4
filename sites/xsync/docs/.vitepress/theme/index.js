import DefaultTheme from 'vitepress/theme';
import Layout from './Layout.vue';
import OptionFilter from './OptionFilter.vue';
import HoloChart from './HoloChart.vue';
import './custom.css';
export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('OptionFilter', OptionFilter);
    app.component('HoloChart', HoloChart);
  },
};
