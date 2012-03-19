$(function() {
    var song_template = Handlebars.compile($("#song_template").html());
    var prev_result = {time: 0};

    function search() {
        $.ajax({url: '/play/' + encodeURI($('#term').val()),
                type: 'POST',
                success: function(result) {
                    collection.add(result);
                    $('#term').val('').focus();
                },
               error: function() {
                   alert('Sorry, nothing found');
                   $('#term').focus()
                }})
    }

    var Item = Backbone.Model.extend({
    });
  
    var Queue = Backbone.Collection.extend({
        model: Item,
        url: "/queue"
    });

    var ItemView = Backbone.View.extend({
        tagName: 'li',
        initialize: function() {
            _.bindAll(this, 'render', 'remove');
            this.model.bind('remove', this.remove);
        },
        render: function() {
            $(this.el).html(song_template(this.model.toJSON()))
            return this;
        },
        remove: function() {
            $(this.el).fadeOut(function() {
                $(this).remove();
            });
        }
    });

    var QueueView = Backbone.View.extend({
        el: $('body'),
        initialize: function() {
            this.counter = 0;
            _(this).bindAll('addItem', 'render', 'removeItem');
            this.collection.bind('refresh', this.render);
            this.collection.bind('add', this.addItem);
            this.collection.bind('remove', this.removeItem);

            this.collection.fetch({add: true});
       },
        addItem: function(item) {
            this.counter++;
            var itemView = new ItemView({
                model: item
            });
            $('ul', this.el).append($(itemView.render().el).fadeIn());
        },
        removeItem: function(item) {
            item.trigger('remove');
        },
        render: function() {
            _(this.collection.models).each(function(item){
                this.addItem(item);
            }, this);
        }
    });

    var collection = new Queue();

    var view = new QueueView({
        collection: collection
    });
    
    $('#play').click(search);
    $('#term').keypress(function(e){
        if(e.which == 13){
            search();
        }
    });

    function update_artist_info(artist) {
        if (artist) {
            $.ajax({url: '/artist/' + encodeURI(artist),
                   success: function(result) {
                       $('#picture').hide();
                       if (result.artist) {
                           $('#picture').attr('src', result.artist.image[2]['#text']).fadeIn();
                       }
                   }});
        }
    }

    function poll_playing() {
        $.ajax({url: '/playing',
                type: 'GET',
                success: function(result) {
                    if (result) {
                        if (result.time != prev_result.time) {
                            prev_result = result;
                            $("#now").html(song_template(result))
                            _(collection.models).each(function(item){
                                if (item.get('time') <= result.time) {
                                    collection.remove(item);
                                }
                            }, this);
                            update_artist_info(result.artist);
                        }
                    } else {
                        $("#now").text("Nothing")
                        $("#picture").hide();
                    }
                },
                error: function() {
                    $("#now").text("Can't get data")
                }});
    }

    poll_playing();
    setInterval(poll_playing, 5000);
});