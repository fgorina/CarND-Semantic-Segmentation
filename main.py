import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights
    vgg_tag = 'vgg16'

    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)

    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    graph = tf.get_default_graph()

    w1 = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer_3 = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer_4 = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer_7 = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)                               
    
    return w1, keep, layer_3, layer_4, layer_7

tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function

    # Add a 1 by 1 layer to preserve spatial information

    pool3_out_scaled = tf.multiply(vgg_layer3_out, 0.0001, name='pool3_out_scaled')
    pool4_out_scaled = tf.multiply(vgg_layer4_out, 0.01, name='pool4_out_scaled')

    layer7_1_by_1 = tf.layers.conv2d(vgg_layer7_out, num_classes, kernel_size=(1,1), strides=(1,1), padding='SAME', 
        kernel_initializer=tf.random_normal_initializer(stddev=0.01),
	kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    layer4_1_by_1 = tf.layers.conv2d(pool4_out_scaled, num_classes, 1, padding='SAME',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),          
        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    layer3_1_by_1 = tf.layers.conv2d(pool3_out_scaled, num_classes, 1, padding='SAME',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),          
        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))


    dcon_1 = tf.layers.conv2d_transpose(layer7_1_by_1, num_classes, 4, strides=(2,2), padding='SAME',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    dcon_1_added = tf.add(dcon_1, layer4_1_by_1)

    dcon_2 = tf.layers.conv2d_transpose(dcon_1_added, num_classes, 4, strides=(2,2), padding='SAME',
       kernel_initializer= tf.random_normal_initializer(stddev=0.01),
       kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    dcon_2_added = tf.add(dcon_2, layer3_1_by_1)

    dcon_3 = tf.layers.conv2d_transpose(dcon_2_added, num_classes, 16, strides=(8,8), padding='SAME',
       kernel_initializer= tf.random_normal_initializer(stddev=0.01),
       kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    return dcon_3

tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function
    
    """ It seems that L2 regularizations  are not applied automativcally.
    	We must get the values from tf.GraphKeys.REGULARIZATION_LOSSES and add them to the loss """

    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    labels = tf.reshape(correct_label, (-1, num_classes))
    reg_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    reg_constant = 0.001
    entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=labels))
    loss = entropy_loss + reg_constant * sum(reg_losses)
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    train_op = optimizer.minimize(loss)

    return logits, train_op, loss

tests.test_optimize(optimize)



def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function

    for epoch in range(epochs):
        print("Epoch : ", epoch)
        for image, label in get_batches_fn(batch_size):
            _, loss = sess.run([train_op, cross_entropy_loss], feed_dict={input_image: image, correct_label: label, 
                learning_rate: 0.0009, keep_prob: 0.8})
            print("Loss : ", loss)


tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/
    epochs = 300
    batch_size = 25

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        image, keep_prob, vgg_layer3_out, vgg_layer4_out, vgg_layer7_out = load_vgg(sess, vgg_path)
        nn_last_layer = layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes)
        # TODO: Train NN using the train_nn function
        correct_label = tf.placeholder(tf.float32, [None, None, None, num_classes], name='correct_label')
        learning_rate = tf.placeholder(tf.float32, name='learning_rate')
        # keep_prob = tf.placeholder(tf.float32, name='keep_prob')
        logits, train_op, entropy_loss = optimize(nn_last_layer, correct_label, learning_rate, num_classes)

        sess.run(tf.global_variables_initializer())

        train_nn(sess, epochs, batch_size, get_batches_fn, train_op, entropy_loss,image, 
             correct_label, keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, image)

        # OPTIONAL: Apply the trained model to a video. Sorry not this time.


if __name__ == '__main__':
    run()

