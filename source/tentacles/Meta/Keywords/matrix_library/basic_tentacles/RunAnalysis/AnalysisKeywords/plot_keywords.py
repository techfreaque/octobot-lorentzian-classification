import octobot_commons.enums as commons_enums


def plot_from_standard_data(data_set: list, plotted_element, title: str):
    x = []
    y = []
    open = []
    high = []
    low = []
    close = []
    volume = []
    text = []
    color = []
    size = []
    shape = []
    if data_set and len(data_set):
        if data_set[0].get(commons_enums.PlotAttributes.X.value, None) is None:
            x = None
        if data_set[0].get(commons_enums.PlotAttributes.Y.value, None) is None:
            y = None
        if data_set[0].get(commons_enums.PlotAttributes.OPEN.value, None) is None:
            open = None
        if data_set[0].get(commons_enums.PlotAttributes.HIGH.value, None) is None:
            high = None
        if data_set[0].get(commons_enums.PlotAttributes.LOW.value, None) is None:
            low = None
        if data_set[0].get(commons_enums.PlotAttributes.CLOSE.value, None) is None:
            close = None
        if data_set[0].get(commons_enums.PlotAttributes.VOLUME.value, None) is None:
            volume = None
        if data_set[0].get(commons_enums.PlotAttributes.TEXT.value, None) is None:
            text = None
        if data_set[0].get(commons_enums.PlotAttributes.COLOR.value, None) is None:
            color = None
        if data_set[0].get(commons_enums.PlotAttributes.SIZE.value, None) is None:
            size = None
        if data_set[0].get(commons_enums.PlotAttributes.SHAPE.value, None) is None:
            shape = None
        line_shape = data_set[0].get("line_shape", None)
        own_yaxis = data_set[0].get(commons_enums.PlotAttributes.OWN_YAXIS.value, False)
        for data in data_set:
            if x is not None:
                x.append(data[commons_enums.PlotAttributes.X.value])
            if y is not None:
                y.append(data[commons_enums.PlotAttributes.Y.value])
            if open is not None:
                open.append(data[commons_enums.PlotAttributes.OPEN.value])
            if high is not None:
                high.append(data[commons_enums.PlotAttributes.HIGH.value])
            if low is not None:
                low.append(data[commons_enums.PlotAttributes.LOW.value])
            if close is not None:
                close.append(data[commons_enums.PlotAttributes.CLOSE.value])
            if volume is not None:
                volume.append(data[commons_enums.PlotAttributes.VOLUME.value])
            if text is not None:
                text.append(data[commons_enums.PlotAttributes.TEXT.value])
            if color is not None:
                color.append(data[commons_enums.PlotAttributes.COLOR.value])
            if size is not None:
                size.append(data[commons_enums.PlotAttributes.SIZE.value])
            if shape is not None:
                shape.append(data[commons_enums.PlotAttributes.SHAPE.value])
        plotted_element.plot(
            kind=data.get(commons_enums.PlotAttributes.KIND.value, None),
            x=x,
            y=y,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            title=title,
            text=text,
            x_type="date",
            y_type="log",
            line_shape=line_shape,
            mode=data.get(commons_enums.PlotAttributes.MODE.value, None),
            own_yaxis=own_yaxis,
            color=color,
            size=size,
            symbol=shape,
        )
