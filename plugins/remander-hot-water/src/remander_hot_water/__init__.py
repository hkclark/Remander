"""Hot water recirculation pump control plugin for Remander."""


def create_plugin():
    """Factory function called by the plugin entry point."""
    from remander_hot_water.plugin import HotWaterPlugin

    return HotWaterPlugin()
